import segno
import os

class QR_Code_Generation:

    def QR_Code(self, form_url, save_path):
        # Placeholder for the form URL (if not passed as an argument)
        form_url = "http://127.0.0.1:5000"  
        # Create the data string, combining the form URL
        event_data = f"Form URL: {form_url}"

        # Generate the QR code
        qr = segno.make(event_data)

        # Check if the provided save_path is a directory
        save_dir = os.path.dirname(save_path)
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)  # Create the directory if it doesn't exist

        # Save the QR code to the specified path
        qr.save(save_path)

        print(f"QR code saved successfully at {save_path}")
