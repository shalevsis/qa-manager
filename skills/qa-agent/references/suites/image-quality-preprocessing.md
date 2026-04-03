# Suite: Image Quality & Pre-Processing

## When to apply
Use this suite when the app processes or transforms images before uploading. Covers client-side validation, format conversion, and metadata handling.

## What to test

- EXIF rotation metadata applied before upload (image arrives server-side upright)
- HEIC/HEIF format detected and converted to JPEG before upload
- Corrupted or truncated file rejected with a clear, specific error message
- 1x1 pixel image (valid format, invalid content) rejected with a dimension error
- Image exceeding the size limit (e.g., 50 MB+) is either rejected with a size error or compressed before upload
- File with wrong extension (e.g., PNG data saved as `.jpg`) handled by content-type inspection, not filename
- Blurry, dark, or overexposed image is passed through to the AI without client-side rejection
- Screenshot and real photo treated identically through the pipeline
- Processed image dimensions and orientation match expectations after transformation

## Key patterns

```
// EXIF rotation
const img = loadFixture('landscape-with-exif-rotation.jpg')
const processed = preprocess(img)
expect(processed.exifOrientation).toBe(1) // normalized
expect(processed.visualOrientation).toBe('upright')

// HEIC conversion
const heic = loadFixture('photo.heic')
const processed = preprocess(heic)
expect(processed.mimeType).toBe('image/jpeg')

// Corrupted file
const bad = loadFixture('truncated.jpg')
expect(() => preprocess(bad)).toThrowError(/corrupt|invalid/i)

// Dimension rejection
const tiny = createImage({ width: 1, height: 1 })
expect(() => preprocess(tiny)).toThrowError(/too small|dimension/i)

// Size rejection or compression
const huge = loadFixture('50mb-photo.jpg')
const result = preprocess(huge)
expect(result.size).toBeLessThanOrEqual(MAX_UPLOAD_BYTES)
// OR: expect(preprocess(huge)).toThrowError(/too large/i)

// Content-type check (not filename)
const pngData = loadFixture('real.png')
pngData.name = 'photo.jpg' // wrong extension
const processed = preprocess(pngData)
expect(processed.mimeType).toBe('image/png') // detected from bytes

// Blur/dark passed through (no client-side quality gate)
const blurry = loadFixture('blurry.jpg')
expect(() => preprocess(blurry)).not.toThrow()

// Screenshot treated same as photo
const screenshot = loadFixture('screenshot.png')
expect(preprocess(screenshot)).toBeDefined()
```

## Common gaps

- EXIF rotation only tested with a right-side-up image (passes trivially); must use a fixture with rotation flag set
- HEIC conversion not tested on all target platforms — conversion library may be missing on some browsers/OS versions
- Corrupted file error message is generic ("Upload failed") rather than distinguishing corruption from size/format issues
- 1x1 image passes client validation but crashes the AI model downstream
- Size limit enforced by rejecting the file but compression path never exercised or tested
- Content-type detection relies on file extension in the MIME type string, not magic-byte inspection
- Blur/dark images are incorrectly blocked by a client-side heuristic that was never intended to be there
- EXIF stripping (for privacy) not verified — rotation corrected but all other EXIF data still present in upload
