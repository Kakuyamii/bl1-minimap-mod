from datetime import datetime, timezone
import faulthandler
import json
import os
from pathlib import Path
import shutil
import traceback


class Diagnostics:
    def __init__(self, directory=None):
        self.directory = directory
        self.path = None
        self._file = self._fault_file = None
        self._owns_fault_handler = False
        self._seen = set()

    @property
    def active(self):
        return self._file is not None

    def start(self):
        if self._file is not None:
            return
        default_directory = self.directory is None
        if default_directory:
            from mods_base import SETTINGS_DIR
            self.directory = Path(SETTINGS_DIR).parent / "crash dumps" / "Minimap"
        folder = Path(self.directory)
        folder.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        self.path = folder / f"minimap-{stamp}-{os.getpid()}.jsonl"
        self._file = self.path.open("x", encoding="utf-8", buffering=1)
        self._seen.clear()
        self.record("session.begin", version="0.2.10", pid=os.getpid())
        if default_directory:
            self.collect_native_dumps(Path.home() / "Documents" / "my games" /
                                      "borderlands" / "WillowGame" / "Logs")

        if not faulthandler.is_enabled():
            try:
                self._fault_file = self.path.with_suffix(".python-fault.txt").open("x")
                faulthandler.enable(file=self._fault_file, all_threads=True)
                self._owns_fault_handler = True
                self.record("python_fault_handler.enabled")
            except (OSError, RuntimeError) as exc:
                self.record("python_fault_handler.unavailable", error=str(exc))
        else:
            self.record("python_fault_handler.already_owned_elsewhere")

    def collect_native_dumps(self, source):

        try:
            dumps = sorted(Path(source).glob("*.dmp"),
                           key=lambda p: p.stat().st_mtime, reverse=True)[:3]
            target = Path(self.directory) / "native"
            for path in dumps:
                size = path.stat().st_size
                if not 0 < size <= 64 * 1024 * 1024:
                    continue
                target.mkdir(parents=True, exist_ok=True)
                destination = target / path.name
                if not destination.exists():
                    shutil.copy2(path, destination)
                    self.record("native_dump.collected", source=str(path), bytes=size)
        except OSError as exc:
            self.record("native_dump.collection_failed", error=str(exc))

    def record(self, stage, **fields):
        if self._file is None:
            return
        try:
            self._file.write(json.dumps(dict(time=datetime.now(timezone.utc).isoformat(),
                                            stage=stage, **fields), default=str) + "\n")
            self._file.flush()
            os.fsync(self._file.fileno())
        except OSError:

            pass

    def checkpoint(self, stage, **fields):

        if stage not in self._seen and self._file is not None:
            self.record(stage, **fields)
            self._seen.add(stage)

    def error(self, exc):
        self.record("python.exception", error=str(exc),
                    traceback="".join(traceback.format_exception(exc)))

    def stop(self):
        self.record("session.disabled")
        if self._owns_fault_handler:
            faulthandler.disable()
            self._owns_fault_handler = False
        if self._fault_file is not None:
            self._fault_file.close()
            self._fault_file = None
        if self._file is not None:
            self._file.close()
            self._file = None
