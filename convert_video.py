from moviepy import VideoFileClip

def convert_webm_to_mp4(input_path, output_path):
    print(f"Converting {input_path} to {output_path}...")
    clip = VideoFileClip(input_path)
    # Write using libx264 which is compatible with mp4
    clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
    clip.close()
    print("Conversion complete.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python convert_video.py <input.webm> <output.mp4>")
        sys.exit(1)
    
    convert_webm_to_mp4(sys.argv[1], sys.argv[2])
