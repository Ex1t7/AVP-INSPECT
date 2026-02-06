


import sys
import time
import argparse
import csv
import json
import os
from datetime import datetime
from state_explorer_refactored import StateExplorerApp
from mouse_controller import MouseController
from esp32_mouse import ESP32Mouse
from screenshot_manager import ScreenshotManager
from config import Config


STATUS_FILE = "batch_run_status.json"

def get_status_file_for_csv(csv_path):
    
    
    base_name = os.path.splitext(os.path.basename(csv_path))[0]
    return f"{base_name}_status.json"

def load_apps_from_csv(csv_path):
    
    apps = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            
            app_name = (
                row.get('CFBundleDisplayName') or
                row.get('Decoded_App_Name') or
                row.get('CFBundle_Name') or
                row.get('App_Name') or
                ''
            )
            if app_name and app_name.strip():
                apps.append(app_name.strip())
    return apps

def load_status(status_file):
    
    if os.path.exists(status_file):
        with open(status_file, 'r') as f:
            return json.load(f)
    return {}

def save_status(status, status_file):
    
    with open(status_file, 'w') as f:
        json.dump(status, f, indent=2)

def main():
    
    parser = argparse.ArgumentParser(
        description="Batch App Explorer - Run multiple apps sequentially"
    )
    parser.add_argument(
        '--enable-recording',
        action='store_true',
        help='Enable video recording for all apps (requires video_recorder_service.py running)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=20,
        help='Exploration timeout in minutes per app (default: 20)'
    )
    parser.add_argument(
        '--app-list',
        type=str,
        default='../visionos_apps_master_list.csv',
        help='Path to CSV file containing app list (default: ../visionos_apps_master_list.csv)'
    )
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from previous run (skip completed apps)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of apps to run (for testing)'
    )
    args = parser.parse_args()

    
    status_file = get_status_file_for_csv(args.app_list)
    
    
    print("Loading app list from CSV...")
    apps_to_explore = load_apps_from_csv(args.app_list)

    if args.limit:
        apps_to_explore = apps_to_explore[:args.limit]

    print(f"Loaded {len(apps_to_explore)} apps")

    
    status = load_status(status_file) if args.resume else {}

    
    if args.resume and status:
        completed = [app for app, info in status.items() if info.get('status') == 'Success']
        print(f"Found {len(completed)} previously completed apps")
        apps_to_explore = [app for app in apps_to_explore if app not in completed]
        print(f"Will explore {len(apps_to_explore)} remaining apps")

    print("=== Batch App Explorer (Refactored) ===")
    print(f"Status file: {status_file}")
    print(f"Will explore {len(apps_to_explore)} apps with {args.timeout}-minute timeout each")
    if args.enable_recording:
        print("📹 Video recording: ENABLED")
    if args.resume:
        print("🔄 Resume mode: ENABLED")
    print(f"\nApps to explore:")
    for i, app in enumerate(apps_to_explore[:10], 1):
        print(f"  {i}. {app}")
    if len(apps_to_explore) > 10:
        print(f"  ... and {len(apps_to_explore) - 10} more")

    print("\nStarting exploration in 5 seconds...")
    time.sleep(5)

    
    print("\n=== Initial Setup ===")
    print("Setting up ESP32 and components (one-time setup)...")

    try:
        
        temp_app = StateExplorerApp("temp", timeout_minutes=args.timeout)
        temp_app.esp32 = ESP32Mouse(port=temp_app.config.app.esp32_port, debug=temp_app.config.app.esp32_debug)
        temp_app.screenshot_manager = ScreenshotManager(temp_app.config)
        temp_app.config.update_from_env()
        temp_app.mouse_controller = MouseController(temp_app.config, temp_app.esp32)
        if not temp_app.setup():
            print("❌ Failed to setup system, exiting...")
            return
        print("✅ System setup complete!")
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return

    for i, app_name in enumerate(apps_to_explore, 1):
        print(f"\n{'='*60}")
        print(f"App {i}/{len(apps_to_explore)}: {app_name}")
        print(f"{'='*60}")

        start_time = datetime.now()

        try:
            
            
            app = StateExplorerApp(app_name, timeout_minutes=args.timeout)

            
            if args.enable_recording:
                app.config.video_recorder.enabled = True
                print(f"📹 Video recording enabled for {app_name}")

            
            print(f"Setting up {app_name}...")
            if not app.setup():
                print(f"❌ Failed to setup {app_name}")
                status[app_name] = {
                    "status": "Setup Failed",
                    "timestamp": datetime.now().isoformat(),
                    "duration": (datetime.now() - start_time).total_seconds()
                }
                save_status(status, status_file)
                continue

            
            app.print_system_info()

            
            print(f"\nStarting exploration of {app_name}...")
            success = app.run()

            end_time = datetime.now()
            result_status = "Success" if success else "Failed"
            status[app_name] = {
                "status": result_status,
                "timestamp": end_time.isoformat(),
                "duration": (end_time - start_time).total_seconds()
            }
            save_status(status, status_file)
            print(f"\n✅ Completed: {app_name} - {result_status}")

        except KeyboardInterrupt:
            print(f"\n\n🛑 Interrupted by user during {app_name}")
            status[app_name] = {
                "status": "Interrupted",
                "timestamp": datetime.now().isoformat(),
                "duration": (datetime.now() - start_time).total_seconds()
            }
            save_status(status, status_file)
            break

        except Exception as e:
            print(f"\n❌ Error exploring {app_name}: {e}")
            import traceback
            traceback.print_exc()
            status[app_name] = {
                "status": f"Error: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "duration": (datetime.now() - start_time).total_seconds()
            }
            save_status(status, status_file)

        
        if i < len(apps_to_explore):
            print(f"\nMoving to next app in 5 seconds...")
            time.sleep(5)

    
    print(f"\n\n{'='*60}")
    print("EXPLORATION SUMMARY")
    print(f"{'='*60}")

    success_apps = []
    failed_apps = []

    for app_name, info in status.items():
        app_status = info.get('status', 'Unknown')
        status_icon = "✅" if app_status == "Success" else "❌"
        duration = info.get('duration', 0)
        print(f"{status_icon} {app_name}: {app_status} ({duration:.1f}s)")

        if app_status == "Success":
            success_apps.append(app_name)
        else:
            failed_apps.append(app_name)

    print(f"\nTotal: {len(success_apps)}/{len(status)} apps explored successfully")
    print(f"Failed/Incomplete: {len(failed_apps)}")
    print(f"{'='*60}")

    
    if failed_apps:
        print(f"\n📝 Apps that need to be re-run:")
        for app in failed_apps:
            print(f"  - {app}")

        
        with open("failed_apps.txt", "w") as f:
            for app in failed_apps:
                f.write(f"{app}\n")
        print(f"\n💾 Failed apps saved to: failed_apps.txt")

    print(f"💾 Full status saved to: {status_file}")

if __name__ == "__main__":
    main()
