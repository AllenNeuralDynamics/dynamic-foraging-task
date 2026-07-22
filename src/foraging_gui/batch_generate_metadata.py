from pathlib import Path
import traceback

from foraging_gui.GenerateMetadata import generate_metadata


def find_session_json_files(root_folder):
    """
    Find behavior JSON files with this expected structure:

    root_folder/
        mouse_id/
            behavior_mouseid_date_time/
                behavior/
                    mouseid_date_time.json
                metadata-dir/
    """
    root_folder = Path(root_folder)

    if not root_folder.exists():
        raise FileNotFoundError(f"Root folder does not exist: {root_folder}")

    json_files = []

    # Example:
    # C:/behavior_data/323_11D/856494/
    # behavior_856494_2026-07-13_13-29-24/
    # behavior/856494_2026-07-13_13-29-24.json
    for json_file in root_folder.glob("*/behavior_*/behavior/*.json"):
        session_folder = json_file.parent.parent

        # The expected JSON filename is the session-folder name
        # without the "behavior_" prefix.
        #
        # session folder:
        # behavior_856494_2026-07-13_13-29-24
        #
        # expected JSON:
        # 856494_2026-07-13_13-29-24.json
        session_name = session_folder.name

        if not session_name.startswith("behavior_"):
            continue

        expected_json_name = session_name.removeprefix("behavior_") + ".json"

        # Ignore unrelated JSON files that may also be in the behavior folder.
        if json_file.name != expected_json_name:
            print(f"Ignoring unexpected JSON file: {json_file}")
            continue

        json_files.append(json_file)

    return sorted(json_files)


def batch_generate_metadata(root_folder, dialog_metadata_file):
    """
    Generate metadata for every session under root_folder.

    Parameters
    ----------
    root_folder : str or Path
        Parent folder containing mouse folders.

    dialog_metadata_file : str or Path
        Shared metadata-dialog JSON file used for all sessions.
    """
    root_folder = Path(root_folder)
    dialog_metadata_file = Path(dialog_metadata_file)

    if not dialog_metadata_file.is_file():
        raise FileNotFoundError(
            f"Dialog metadata file does not exist: {dialog_metadata_file}"
        )

    json_files = find_session_json_files(root_folder)

    print("=" * 80)
    print(f"Root folder: {root_folder}")
    print(f"Dialog metadata: {dialog_metadata_file}")
    print(f"Found {len(json_files)} session JSON files")
    print("=" * 80)

    if not json_files:
        print("No matching session JSON files were found.")
        return []

    results = []

    for session_number, json_file in enumerate(json_files, start=1):
        session_folder = json_file.parent.parent
        mouse_folder = session_folder.parent
        output_folder = session_folder / "metadata-dir"

        # Required because generate_metadata does not create the
        # folder when output_folder is explicitly provided.
        output_folder.mkdir(parents=True, exist_ok=True)

        print()
        print("-" * 80)
        print(f"[{session_number}/{len(json_files)}] Mouse: {mouse_folder.name}")
        print(f"Session: {session_folder.name}")
        print(f"Input:   {json_file}")
        print(f"Output:  {output_folder}")

        try:
            metadata_result = generate_metadata(
                json_file=str(json_file),
                dialog_metadata_file=str(dialog_metadata_file),
                output_folder=str(output_folder),
            )

            session_success = bool(
                getattr(metadata_result, "session_metadata_success", False)
            )
            rig_success = bool(
                getattr(metadata_result, "rig_metadata_success", False)
            )

            if session_success and rig_success:
                status = "success"
                print("Result: session and rig metadata generated")
            elif session_success:
                status = "partial"
                print("Result: session metadata generated, but rig metadata failed")
            elif rig_success:
                status = "partial"
                print("Result: rig metadata generated, but session metadata failed")
            else:
                status = "failed"
                print("Result: metadata generation did not report success")

            results.append(
                {
                    "mouse_id": mouse_folder.name,
                    "session": session_folder.name,
                    "json_file": str(json_file),
                    "output_folder": str(output_folder),
                    "status": status,
                    "session_metadata_success": session_success,
                    "rig_metadata_success": rig_success,
                    "error": "",
                }
            )

        except Exception as error:
            print(f"ERROR: {error}")
            traceback.print_exc()

            results.append(
                {
                    "mouse_id": mouse_folder.name,
                    "session": session_folder.name,
                    "json_file": str(json_file),
                    "output_folder": str(output_folder),
                    "status": "error",
                    "session_metadata_success": False,
                    "rig_metadata_success": False,
                    "error": str(error),
                }
            )

    successful = sum(r["status"] == "success" for r in results)
    partial = sum(r["status"] == "partial" for r in results)
    failed = len(results) - successful - partial

    print()
    print("=" * 80)
    print("BATCH METADATA GENERATION COMPLETE")
    print(f"Total sessions: {len(results)}")
    print(f"Successful:     {successful}")
    print(f"Partial:        {partial}")
    print(f"Failed:         {failed}")
    print("=" * 80)

    failed_results = [r for r in results if r["status"] != "success"]

    if failed_results:
        print("\nSessions requiring review:")
        for result in failed_results:
            print(f"  {result['status'].upper()}: {result['session']}")
            if result["error"]:
                print(f"    Error: {result['error']}")

    return results


if __name__ == "__main__":
    ROOT_FOLDER = Path(r"C:\behavior_data\323_11D")

    DIALOG_METADATA_FILE = Path(
        r"C:\Users\svc_aind_behavior"
        r"\Documents\ForagingSettings"
        r"\metadata_dialog"
        r"\323_11D_2026-07-22_11-04-49_metadata_dialog.json"
    )

    batch_results = batch_generate_metadata(
        root_folder=ROOT_FOLDER,
        dialog_metadata_file=DIALOG_METADATA_FILE,
    )
