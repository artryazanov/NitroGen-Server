
import pytest
import torch
import numpy as np
from collections import deque

def test_initialization(inference_session):
    """Test that the session initializes correctly."""
    assert inference_session.max_buffer_size == 16
    assert inference_session.selected_game == "game1"
    assert len(inference_session.obs_buffer) == 0
    assert len(inference_session.action_buffer) == 0
    assert inference_session.is_flowmatching is True

def test_reset(inference_session):
    """Test that reset clears buffers."""
    inference_session.obs_buffer.append(torch.randn(1, 3, 256, 256))
    inference_session.action_buffer.append({"buttons": torch.zeros(1)})
    
    assert len(inference_session.obs_buffer) > 0
    assert len(inference_session.action_buffer) > 0
    
    inference_session.reset()
    
    assert len(inference_session.obs_buffer) == 0
    assert len(inference_session.action_buffer) == 0

def test_predict_flow(inference_session, mock_img_proc, mock_tokenizer, mock_model):
    """Test the main prediction loop flow."""
    dummy_obs = np.zeros((256, 256, 3), dtype=np.uint8)
    
    result = inference_session.predict(dummy_obs)
    
    # Check if image processor was called
    mock_img_proc.assert_called_once()
    
    # Check if buffer was updated
    assert len(inference_session.obs_buffer) == 1
    
    # Check if model was called (since cfg_scale != 1.0, get_action_with_cfg should be called)
    mock_model.get_action_with_cfg.assert_called_once()
    
    # Check if result has expected keys
    assert "buttons" in result
    assert "j_left" in result
    assert "j_right" in result
    assert len(inference_session.action_buffer) == 1
    
def test_predict_cfg_scale_one(inference_session, mock_model):
    """Test prediction path when cfg_scale is 1.0."""
    inference_session.cfg_scale = 1.0
    dummy_obs = np.zeros((256, 256, 3), dtype=np.uint8)
    
    inference_session.predict(dummy_obs)
    
    # Should call get_action instead of get_action_with_cfg
    mock_model.get_action.assert_called_once()
    mock_model.get_action_with_cfg.assert_not_called()

def test_info(inference_session):
    """Test info method returns correct metadata."""
    info = inference_session.info()
    assert info["ckpt_path"] == "dummy_path.pt"
    assert info["context_length"] == 16
    assert info["cfg_scale"] == 1.5
