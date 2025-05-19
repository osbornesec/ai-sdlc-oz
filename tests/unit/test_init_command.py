import pytest
from pathlib import Path
from ai_sdlc.commands import init
from ai_sdlc import utils

def test_run_init(temp_project_dir: Path, mocker):
    mocker.patch('ai_sdlc.utils.ROOT', temp_project_dir)
    mock_write_lock = mocker.patch('ai_sdlc.utils.write_lock')
    
    # Mock any directory operations to prevent actual file system changes
    mocker.patch.object(Path, 'mkdir')
    
    init.run_init()
    
    # Verify directories would have been created
    Path.mkdir.assert_any_call(parents=True, exist_ok=True)
    
    # Verify lock file would have been written
    mock_write_lock.assert_called_once_with({})