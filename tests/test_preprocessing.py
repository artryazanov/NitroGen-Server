import sys
import os
import pytest
from unittest.mock import MagicMock, call

# Add scripts to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../scripts"))

# Import serve (mocks are already applied by conftest.py)
try:
    import serve
except ImportError:
    serve = None

import cv2
import numpy as np

@pytest.mark.skipif(serve is None, reason="Dependencies missing")
class TestPreprocessing:
    
    def setup_method(self):
        # Reset mocks before each test
        cv2.reset_mock()
        # Setup common mock behavior
        # cv2.resize returns a new mock
        cv2.resize.return_value = MagicMock(shape=(256, 256, 3))
        cv2.copyMakeBorder.return_value = MagicMock(shape=(256, 256, 3))

    def test_preprocess_stretch(self):
        # Setup Mock Image
        img = MagicMock()
        img.shape = (200, 100, 3) # Height 200, Width 100
        
        # Call
        res = serve.preprocess_image(img, "stretch")
        
        # Verify
        cv2.resize.assert_called_once()
        args, kwargs = cv2.resize.call_args
        assert args[0] == img # First arg is image
        assert args[1] == (256, 256) # Target size
        assert kwargs.get('interpolation') == cv2.INTER_AREA

    def test_preprocess_stretch_no_op(self):
        # If already 256x256
        img = MagicMock()
        img.shape = (256, 256, 3)
        
        res = serve.preprocess_image(img, "stretch")
        
        # Should return original image without resize
        cv2.resize.assert_not_called()
        assert res == img

    def test_preprocess_crop(self):
        # 100x200 (Height 100, Width 200)
        img = MagicMock()
        img.shape = (100, 200, 3)
        # Slicing returns a new mock
        sliced_img = MagicMock()
        sliced_img.shape = (100, 100, 3) # After crop it should be square
        img.__getitem__.return_value = sliced_img
        
        res = serve.preprocess_image(img, "crop")
        
        # Verify Slicing (Center Crop)
        # min_dim = 100. Center w=100. start_w = 50. end_w = 150.
        # Img should be sliced [0:100, 50:150]
        # Since we can't easily check slice args on __getitem__ with simple mocks without complex setup,
        # we focus on the fact that it was sliced and then resized.
        
        img.__getitem__.assert_called()
        
        # And then resized
        cv2.resize.assert_called_once()
        args, kwargs = cv2.resize.call_args
        assert args[0] == sliced_img # Should resize the sliced result
        assert args[1] == (256, 256)

    def test_preprocess_pad(self):
        # 200x100 (Height 200, Width 100)
        img = MagicMock()
        img.shape = (200, 100, 3)
        
        padded_img = MagicMock()
        padded_img.shape = (200, 200, 3) # Square after padding
        cv2.copyMakeBorder.return_value = padded_img
        
        res = serve.preprocess_image(img, "pad")
        
        # Verify Padding
        # max_dim = 200. Padding on left/right.
        # Height 200. Width 100.
        # top=0, bottom=0.
        # left=(200-100)//2=50. right=50.
        
        cv2.copyMakeBorder.assert_called_once_with(
            img, 0, 0, 50, 50, cv2.BORDER_CONSTANT, value=[0, 0, 0]
        )
        
        # And then resized
        cv2.resize.assert_called_once()
        args, kwargs = cv2.resize.call_args
        assert args[0] == padded_img
        assert args[1] == (256, 256)

    def test_preprocess_default(self):
        # Default -> Pad
        img = MagicMock()
        img.shape = (200, 100, 3)
        
        padded_img = MagicMock()
        padded_img.shape = (200, 200, 3)
        cv2.copyMakeBorder.return_value = padded_img
        
        res = serve.preprocess_image(img) # No mode
        
        cv2.copyMakeBorder.assert_called_once() # Should use pad logic
