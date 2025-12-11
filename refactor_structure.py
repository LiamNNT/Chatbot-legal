#!/usr/bin/env python3
"""
Refactor Structure Script for Chatbot-UIT Project
Moves files and directories according to the microservices architecture plan.
"""

import os
import shutil
from pathlib import Path
import glob


def ensure_dir(path: Path):
    """Create directory if it doesn't exist."""
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        print(f"[CREATE] Created directory: {path}")
        return True
    return False


def safe_move(source: Path, dest: Path, base_dir: Path):
    """Safely move a file or directory."""
    try:
        if not source.exists():
            return False, f"Source not found: {source}"
        
        # Create destination parent directory
        ensure_dir(dest.parent)
        
        # If destination exists and is a file, backup it
        if dest.exists():
            if dest.is_file():
                backup = dest.with_suffix(dest.suffix + ".backup")
                shutil.copy2(dest, backup)
                print(f"[BACKUP] {dest.name} -> {backup.name}")
            else:
                return False, f"Destination directory already exists: {dest}"
        
        shutil.move(str(source), str(dest))
        print(f"[MOVE] {source.relative_to(base_dir)} -> {dest.relative_to(base_dir)}")
        return True, None
        
    except Exception as e:
        return False, str(e)


def refactor_structure():
    """Execute the refactoring plan."""
    
    # Base directory
    BASE_DIR = Path(__file__).parent.resolve()
    
    print("=" * 70)
    print("  CHATBOT-UIT PROJECT RESTRUCTURE")
    print("  Following Microservices Architecture")
    print("=" * 70)
    print(f"\nBase directory: {BASE_DIR}\n")
    
    # Confirmation
    confirm = input("This will restructure your project. Continue? (y/N): ")
    if confirm.lower() != 'y':
        print("Aborted.")
        return
    
    successful = []
    failed = []
    skipped = []
    
    # =========================================================================
    # 1. ROOT CLEANUP
    # =========================================================================
    print("\n" + "=" * 70)
    print("  STEP 1: ROOT CLEANUP")
    print("=" * 70)
    
    # 1.1 Move all root *.md files (except README.md) to docs/
    docs_dir = BASE_DIR / "docs"
    ensure_dir(docs_dir)
    
    for md_file in BASE_DIR.glob("*.md"):
        if md_file.name.lower() != "readme.md":
            dest = docs_dir / md_file.name
            success, error = safe_move(md_file, dest, BASE_DIR)
            if success:
                successful.append(f"{md_file.name} -> docs/")
            elif error:
                if "not found" in error.lower():
                    skipped.append((md_file.name, "docs/", error))
                else:
                    failed.append((md_file.name, "docs/", error))
    
    # 1.2 Move start_backend.py, stop_backend.py to scripts/
    scripts_dir = BASE_DIR / "scripts"
    ensure_dir(scripts_dir)
    
    for script in ["start_backend.py", "stop_backend.py"]:
        source = BASE_DIR / script
        dest = scripts_dir / script
        if source.exists():
            success, error = safe_move(source, dest, BASE_DIR)
            if success:
                successful.append(f"{script} -> scripts/")
            else:
                failed.append((script, "scripts/", error))
        else:
            skipped.append((script, "scripts/", "Source not found"))
    
    # 1.3 Move services/rag_services/docker/ content to infrastructure/
    docker_dir = BASE_DIR / "services" / "rag_services" / "docker"
    infra_dir = BASE_DIR / "infrastructure"
    
    if docker_dir.exists():
        ensure_dir(infra_dir)
        for item in docker_dir.iterdir():
            dest = infra_dir / item.name
            success, error = safe_move(item, dest, BASE_DIR)
            if success:
                successful.append(f"docker/{item.name} -> infrastructure/")
            else:
                failed.append((f"docker/{item.name}", "infrastructure/", error))
        # Remove empty docker directory
        if docker_dir.exists() and not any(docker_dir.iterdir()):
            docker_dir.rmdir()
            print(f"[REMOVE] Empty directory: {docker_dir.relative_to(BASE_DIR)}")
    else:
        skipped.append(("services/rag_services/docker/", "infrastructure/", "Source not found"))
    
    # =========================================================================
    # 2. RAG_SERVICES REORGANIZATION
    # =========================================================================
    print("\n" + "=" * 70)
    print("  STEP 2: RAG_SERVICES REORGANIZATION")
    print("=" * 70)
    
    rag_services = BASE_DIR / "services" / "rag_services"
    rag_scripts = rag_services / "scripts"
    
    if not rag_scripts.exists():
        print(f"[SKIP] RAG scripts directory not found: {rag_scripts}")
        skipped.append(("services/rag_services/scripts/", "N/A", "Directory not found"))
    else:
        # 2.1 Create app/core/extraction/ and move files
        extraction_dir = rag_services / "app" / "core" / "extraction"
        ensure_dir(extraction_dir)
        
        extraction_files = [
            "hybrid_extractor.py",
            "vlm_recursive_extractor.py", 
            "page_merger.py"
        ]
        
        for filename in extraction_files:
            source = rag_scripts / filename
            dest = extraction_dir / filename
            if source.exists():
                success, error = safe_move(source, dest, BASE_DIR)
                if success:
                    successful.append(f"scripts/{filename} -> app/core/extraction/")
                else:
                    failed.append((f"scripts/{filename}", "app/core/extraction/", error))
            else:
                skipped.append((f"scripts/{filename}", "app/core/extraction/", "Source not found"))
        
        # 2.2 Create app/core/indexing/ and move files
        indexing_dir = rag_services / "app" / "core" / "indexing"
        ensure_dir(indexing_dir)
        
        indexing_files = [
            "graph_builder.py",
            "index_semantic_data.py",
            "sync_entity_nodes.py"
        ]
        
        for filename in indexing_files:
            source = rag_scripts / filename
            dest = indexing_dir / filename
            if source.exists():
                success, error = safe_move(source, dest, BASE_DIR)
                if success:
                    successful.append(f"scripts/{filename} -> app/core/indexing/")
                else:
                    failed.append((f"scripts/{filename}", "app/core/indexing/", error))
            else:
                skipped.append((f"scripts/{filename}", "app/core/indexing/", "Source not found"))
        
        # 2.3 Create app/core/utils/ and move json_utils.py
        utils_dir = rag_services / "app" / "core" / "utils"
        ensure_dir(utils_dir)
        
        source = rag_scripts / "json_utils.py"
        dest = utils_dir / "json_utils.py"
        if source.exists():
            success, error = safe_move(source, dest, BASE_DIR)
            if success:
                successful.append("scripts/json_utils.py -> app/core/utils/")
            else:
                failed.append(("scripts/json_utils.py", "app/core/utils/", error))
        else:
            skipped.append(("scripts/json_utils.py", "app/core/utils/", "Source not found"))
        
        # 2.4 Create tests/ and move all test_*.py and debug_*.py files
        tests_dir = rag_services / "tests"
        ensure_dir(tests_dir)
        
        # Move test_*.py files
        test_files = list(rag_scripts.glob("test_*.py"))
        for test_file in test_files:
            dest = tests_dir / test_file.name
            success, error = safe_move(test_file, dest, BASE_DIR)
            if success:
                successful.append(f"scripts/{test_file.name} -> tests/")
            else:
                failed.append((f"scripts/{test_file.name}", "tests/", error))
        
        # Move debug_*.py files
        debug_files = list(rag_scripts.glob("debug_*.py"))
        for debug_file in debug_files:
            dest = tests_dir / debug_file.name
            success, error = safe_move(debug_file, dest, BASE_DIR)
            if success:
                successful.append(f"scripts/{debug_file.name} -> tests/")
            else:
                failed.append((f"scripts/{debug_file.name}", "tests/", error))
        
        # 2.5 Create scripts/jobs/ and move job files
        jobs_dir = rag_scripts / "jobs"
        ensure_dir(jobs_dir)
        
        job_files = [
            "run_full_extraction.py",
            "rerun_stage2.py"
        ]
        
        for filename in job_files:
            source = rag_scripts / filename
            dest = jobs_dir / filename
            if source.exists():
                success, error = safe_move(source, dest, BASE_DIR)
                if success:
                    successful.append(f"scripts/{filename} -> scripts/jobs/")
                else:
                    failed.append((f"scripts/{filename}", "scripts/jobs/", error))
            else:
                skipped.append((f"scripts/{filename}", "scripts/jobs/", "Source not found"))
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 70)
    print("  REFACTORING SUMMARY")
    print("=" * 70)
    
    print(f"\n✅ Successful moves: {len(successful)}")
    for item in successful:
        print(f"   • {item}")
    
    if failed:
        print(f"\n❌ Failed moves: {len(failed)}")
        for source, dest, error in failed:
            print(f"   • {source} -> {dest}")
            print(f"     Error: {error}")
    
    if skipped:
        print(f"\n⏭️  Skipped (source not found): {len(skipped)}")
        for source, dest, reason in skipped:
            print(f"   • {source}")
    
    print("\n" + "=" * 70)
    print("  REFACTORING COMPLETE!")
    print("=" * 70)
    
    # Create __init__.py files for new packages
    print("\n[POST] Creating __init__.py files for new packages...")
    
    init_dirs = [
        rag_services / "app" / "core" / "extraction",
        rag_services / "app" / "core" / "indexing", 
        rag_services / "app" / "core" / "utils",
    ]
    
    for init_dir in init_dirs:
        if init_dir.exists():
            init_file = init_dir / "__init__.py"
            if not init_file.exists():
                init_file.touch()
                print(f"   Created: {init_file.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    refactor_structure()
