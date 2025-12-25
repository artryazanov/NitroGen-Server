
import unittest
from unittest.mock import MagicMock, call
import sys
import os
import struct

# Add scripts to path to import serve
sys.path.append(os.path.join(os.path.dirname(__file__), "../scripts"))
import serve

import numpy as np
import cv2

class TestImageServer(unittest.TestCase):
    def setUp(self):
        if hasattr(np, 'reset_mock'): np.reset_mock()
        if hasattr(cv2, 'reset_mock'): cv2.reset_mock()
        
        self.mock_img_array = MagicMock()
        self.mock_img_array.reshape.return_value = self.mock_img_array
        
        if isinstance(np, MagicMock):
            np.frombuffer = MagicMock(return_value=self.mock_img_array)
            
        if isinstance(cv2, MagicMock):
            cv2.flip.return_value = self.mock_img_array
            cv2.cvtColor.return_value = self.mock_img_array
            cv2.resize.return_value = self.mock_img_array

    def test_read_bmp_bottom_up(self):
        """Test flow for Bottom-Up BMP (Height > 0)."""
        width = 256
        height = 256
        header = b'BM' + (54 + width*height*3).to_bytes(4, 'little') + b'\x00\x00\x00\x00' + (54).to_bytes(4, 'little')
        dib_header = (40).to_bytes(4, 'little') + \
                     (width).to_bytes(4, 'little', signed=True) + \
                     (height).to_bytes(4, 'little', signed=True) + \
                     b'\x01\x00' + b'\x18\x00' + b'\x00\x00\x00\x00' * 6
                     
        pixels_data = b'\x00' * (width * height * 3)
        full_data = header + dib_header + pixels_data
        
        mock_conn = MagicMock()
        data_stream = [full_data]
        def side_effect(n):
            if not data_stream: return b""
            current = data_stream[0]
            if len(current) > n:
                ret = current[:n]
                data_stream[0] = current[n:]
                return ret
            else:
                ret = current
                data_stream.pop(0)
                return ret
        mock_conn.recv.side_effect = side_effect
        
        img = serve.read_image_from_conn(mock_conn)
        
        # Verify BMP specific calls
        np.frombuffer.assert_called()
        cv2.flip.assert_called_with(self.mock_img_array, 0)
        cv2.cvtColor.assert_called()
        cv2.resize.assert_not_called()
        self.assertIsNotNone(img)

    def test_read_bmp_top_down(self):
        """Test flow for Top-Down BMP (Height < 0)."""
        width = 256
        height = -256
        header = b'BM' + (54 + width*abs(height)*3).to_bytes(4, 'little') + b'\x00\x00\x00\x00' + (54).to_bytes(4, 'little')
        dib_header = (40).to_bytes(4, 'little') + \
                     (width).to_bytes(4, 'little', signed=True) + \
                     (height).to_bytes(4, 'little', signed=True) + \
                     b'\x01\x00' + b'\x18\x00' + b'\x00\x00\x00\x00' * 6
                     
        pixels_data = b'\x00' * (width * abs(height) * 3)
        full_data = header + dib_header + pixels_data
        
        mock_conn = MagicMock()
        data_stream = [full_data]
        def side_effect(n):
            if not data_stream: return b""
            current = data_stream[0]
            if len(current) > n:
                ret = current[:n]
                data_stream[0] = current[n:]
                return ret
            else:
                ret = current
                data_stream.pop(0)
                return ret
        mock_conn.recv.side_effect = side_effect
        
        img = serve.read_image_from_conn(mock_conn)
        
        np.frombuffer.assert_called()
        cv2.flip.assert_not_called()
        cv2.cvtColor.assert_called()
        self.assertIsNotNone(img)

    def test_read_raw_image(self):
        """Test reading Raw RGB flow (No BMP header)."""
        width = 256
        height = 256
        expected_bytes = width * height * 3
        
        # Raw bytes, NOT starting with 'BM'
        # Let's start with \x01\x01
        pixels_data = b'\x01' * expected_bytes
        
        mock_conn = MagicMock()
        data_stream = [pixels_data]
        def side_effect(n):
            if not data_stream: return b""
            current = data_stream[0]
            if len(current) > n:
                ret = current[:n]
                data_stream[0] = current[n:]
                return ret
            else:
                ret = current
                data_stream.pop(0)
                return ret
        mock_conn.recv.side_effect = side_effect
        
        img = serve.read_image_from_conn(mock_conn)
        
        np.frombuffer.assert_called()
        
        # Raw path assumes correct format
        cv2.flip.assert_not_called()
        cv2.cvtColor.assert_not_called()
        cv2.resize.assert_not_called()
        
        self.assertIsNotNone(img)

if __name__ == "__main__":
    unittest.main()
