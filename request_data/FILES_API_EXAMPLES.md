# File Upload API Examples

## Upload a file

```bash
# Upload a text file
curl -X POST "http://localhost:8000/files" \
  -H "X-API-Key: your-api-key" \
  -F "file=@request_data/test_file.txt" \
  -F "content_type=text/plain" \
  -F "description=A test text file"

# Upload an image
curl -X POST "http://localhost:8000/files" \
  -H "X-API-Key: your-api-key" \
  -F "file=@path/to/image.jpg" \
  -F "content_type=image/jpeg" \
  -F "description=Profile picture"

# Upload a PDF
curl -X POST "http://localhost:8000/files" \
  -H "X-API-Key: your-api-key" \
  -F "file=@path/to/document.pdf" \
  -F "content_type=application/pdf" \
  -F "description=Important document"

# Upload an audio file
curl -X POST "http://localhost:8000/files" \
  -H "X-API-Key: your-api-key" \
  -F "file=@path/to/audio.mp3" \
  -F "content_type=audio/mpeg" \
  -F "description=Voice recording"

# Upload a video file
curl -X POST "http://localhost:8000/files" \
  -H "X-API-Key: your-api-key" \
  -F "file=@path/to/video.mp4" \
  -F "content_type=video/mp4" \
  -F "description=Tutorial video"
```

## List all files

```bash
curl -X GET "http://localhost:8000/files" \
  -H "X-API-Key: your-api-key"
```

## Notes

- The `content_type` field should be the MIME type of the file (e.g., image/jpeg, application/pdf, audio/wav, video/mp4)
- This MIME type will be used later when including files in LLM prompts
- Files are stored per-user, so you'll only see your own files
- The `description` field is optional

