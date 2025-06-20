import numpy as np
import sounddevice as sd
import pyautogui
import keyboard
import time
import threading
import customtkinter as ctk
from tkinter import scrolledtext

THRESHOLD = 0.2  
DURATION = 1  
SAMPLE_RATE = 44100  
COOLDOWN_TIME = 1.5  
mouse_down_duration = 3 
special_sequence_interval = 900  

is_leftclick_enabled = True
is_special_sequence_enabled = False  
is_running = True
last_click_time = 0
is_click_in_progress = False
is_special_sequence_running = False  
start_time = time.time()
loud_noise_count = 0  
click_lock = threading.Lock() 

def log_message(message):
    """Logs messages to the log box."""
    log_box.insert("end", message + "\n")
    log_box.see("end")

def update_timer():
    """Updates the window title with elapsed time."""
    while True:
        elapsed_time = int(time.time() - start_time)
        root.title(f"Running Time: {elapsed_time}s")
        time.sleep(1)


def update_threshold(value=None):
    """Update the threshold value when the slider is moved or input is changed."""
    global THRESHOLD
    try:
        if value is None:
            value = threshold_entry.get()
            THRESHOLD = float(value)
            threshold_slider.set(THRESHOLD)
        else:
            THRESHOLD = float(value)
            threshold_entry.delete(0, "end")
            threshold_entry.insert(0, f"{THRESHOLD:.2f}")
        threshold_label.config(text=f"Sound Sensitivity: {THRESHOLD:.2f}")
    except ValueError:
        log_message("Invalid threshold value. Please enter a number.")

def click_mouse():
    """Delayed mouse actions."""
    global last_click_time, is_click_in_progress
    with click_lock:
        is_click_in_progress = True
    try:
        pyautogui.rightClick()
        time.sleep(2)
        pyautogui.rightClick()
        last_click_time = time.time()
    finally:
        with click_lock:
            is_click_in_progress = False

def special_sequence():
    """Executes the special key and click sequence at the specified interval."""
    global is_special_sequence_running
    last_run_time = 0
    sequence_enabled_time = 0
    
    while True:
        current_time = time.time()
        
        if not (is_running and is_special_sequence_enabled):
            sequence_enabled_time = 0  
            time.sleep(1)
            continue
            
        if sequence_enabled_time == 0:
            sequence_enabled_time = current_time
            log_message(f"Auto-eat enabled. First sequence will run in {special_sequence_interval//60} minute(s).")
            time.sleep(1)
            continue
            
        if (current_time - sequence_enabled_time >= special_sequence_interval and 
            current_time - last_run_time >= special_sequence_interval):
            
            is_special_sequence_running = True
            log_message("Pausing sound detection for auto-eat sequence")
            try:
                log_message("Starting auto-eat sequence...")
                time.sleep(1)
                log_message("Pressing 2 (food)...")
                pyautogui.keyDown('2')
                time.sleep(0.1)
                pyautogui.keyUp('2')
                time.sleep(1)  
                
                log_message("Clicking to eat... (right-click 3 seconds)")
                pyautogui.mouseDown(button='right')
                time.sleep(4)  
                pyautogui.mouseUp(button='right')
                time.sleep(1) 
                
                log_message("Equipping fishing rod...")
                pyautogui.keyDown('1')
                time.sleep(0.1)
                pyautogui.keyUp('1')
                time.sleep(1)  
                pyautogui.mouseDown(button='right')
                pyautogui.mouseUp(button='right')

                
                log_message(f"Auto-eat sequence completed. Next in {special_sequence_interval//60} minutes.")
                last_run_time = current_time
                sequence_enabled_time = current_time  
                
            except Exception as e:
                log_message(f"Error in sequence: {str(e)}")
                try:
                    pyautogui.keyDown('3')
                    time.sleep(0.1)
                    pyautogui.keyUp('3')
                    time.sleep(1)
                    pyautogui.mouseDown()
                    time.sleep(mouse_down_duration)
                    pyautogui.mouseUp()
                except Exception as recovery_error:
                    log_message(f"Recovery also failed: {str(recovery_error)}")
                last_run_time = current_time - special_sequence_interval + 60  
            finally:
                time.sleep(2) 
                is_special_sequence_running = False
                log_message("Resuming sound detection")
        
        time.sleep(1)

def detect_loud_sound(indata, frames, time_info, status):
    """Callback function to analyze audio in real-time."""
    global THRESHOLD, last_click_time, is_click_in_progress, loud_noise_count, is_special_sequence_running
    if not is_running or is_special_sequence_running:  
        return
    
    volume_norm = np.linalg.norm(indata)
    if volume_norm > THRESHOLD:
        current_time = time.time()
        with click_lock:
            if not is_click_in_progress and current_time - last_click_time >= COOLDOWN_TIME:
                loud_noise_count += 1
                message = f"{loud_noise_count}. Loud sound detected! Clicking..."
                log_message(message)
                if is_leftclick_enabled:
                    threading.Thread(target=click_mouse).start()

def start_audio_stream(device_index):
    """Start the audio input stream from the selected device."""
    with sd.InputStream(callback=detect_loud_sound, channels=1, samplerate=SAMPLE_RATE, device=device_index):
        log_message("Listening for loud sounds...")
        while True:
            if not is_running:
                time.sleep(0.1)
                continue
            time.sleep(0.1)

def get_audio_device_list():
    """Retrieve a list of available audio input devices."""
    devices = sd.query_devices()
    return [device['name'] for device in devices if device['max_input_channels'] > 0]

def toggle_special_sequence():
    global is_special_sequence_enabled
    is_special_sequence_enabled = special_sequence_var.get()
    log_message(f"Auto-eat {'enabled' if is_special_sequence_enabled else 'disabled'}")

def toggle_running():
    global is_running
    is_running = not is_running
    log_message("Program running" if is_running else "Program paused.")

def select_game_audio(device_name):
    """Select the virtual audio device corresponding to the game."""
    device_list = get_audio_device_list()
    if device_name in device_list:
        log_message(f"Found device: {device_name}. Starting audio capture...")
        device_index = device_list.index(device_name)
        audio_thread = threading.Thread(target=start_audio_stream, args=(device_index,), daemon=True)
        audio_thread.start()
    else:
        log_message(f"Device {device_name} not found.")

root = ctk.CTk()
root.title("Sound Threshold Detector")

threading.Thread(target=update_timer, daemon=True).start()
threading.Thread(target=special_sequence, daemon=True).start()

meter = ctk.CTkProgressBar(root, width=300, height=20, orientation="horizontal", mode="indeterminate")

threshold_label = ctk.CTkLabel(root, text=f"Default Sound Sensitivity: {THRESHOLD:.2f}")
threshold_label.grid(row=1, column=0, padx=20, pady=0)

threshold_frame = ctk.CTkFrame(root)
threshold_frame.grid(row=2, column=0, padx=20, pady=10)

threshold_slider = ctk.CTkSlider(threshold_frame, from_=0.0, to=1.0, command=update_threshold, width=200)
threshold_slider.set(THRESHOLD)
threshold_slider.pack(side="left", padx=(0, 10))

threshold_entry = ctk.CTkEntry(threshold_frame, width=60)
threshold_entry.insert(0, f"{THRESHOLD:.2f}")
threshold_entry.pack(side="left")
threshold_entry.bind("<Return>", lambda e: update_threshold())

special_sequence_var = ctk.BooleanVar()
special_sequence_checkbox = ctk.CTkCheckBox(root, text="Enable Auto-Eat", variable=special_sequence_var, command=toggle_special_sequence)
special_sequence_checkbox.grid(row=8, column=0, padx=20, pady=10)

bind_label = ctk.CTkLabel(root, text="Binds: Rod (1), Food (2)")
bind_label.grid(row=9, column=0, padx=20, pady=5)

device_list = get_audio_device_list()
device_dropdown = ctk.CTkOptionMenu(root, values=device_list, command=select_game_audio)
device_dropdown.grid(row=10, column=0, padx=20, pady=10)
device_dropdown.set(device_list[0] if device_list else "No devices found")

log_box = scrolledtext.ScrolledText(root, width=50, height=10, wrap="word", bg="black", fg="white", insertbackground="white")
log_box.grid(row=11, column=0, padx=20, pady=10)
log_box.insert("end", "Log output:\n")

keyboard.add_hotkey("F1", toggle_running)

root.mainloop()
