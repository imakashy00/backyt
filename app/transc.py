from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs

def get_youtube_transcript(youtube_url):
    try:
        # Extract video ID from the URL
        parsed_url = urlparse(youtube_url)
        video_id = parse_qs(parsed_url.query).get('v')
        if not video_id:
            raise ValueError("Invalid YouTube URL. Could not extract video ID.")
        
        video_id = video_id[0]  # Extract video ID from the list

        # Fetch the transcript
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return transcript

    except Exception as e:
        return f"Error: {e}"

# Example usage
youtube_url = "https://www.youtube.com/watch?v=hBMoPUAeLnY"
transcript = get_youtube_transcript(youtube_url)

if isinstance(transcript, list):
    for entry in transcript:
        print(f"{entry['start']}s: {entry['text']}")
else:
    print(transcript)
