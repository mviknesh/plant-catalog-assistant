import os
import time
import subprocess
from playwright.sync_api import sync_playwright
from google.cloud import storage

TARGET_URL = "https://simple-agent-frontend-177806079572.us-central1.run.app"
RECORDINGS_DIR = "/config/.gemini/antigravity/scratch/simple-agent/scratch/recordings"
FIRESTORE_PROJECT = "qwiklabs-gcp-01-9657f097aca6"
GCS_BUCKET_NAME = "plant-catalog-assets-9657f097aca6"

os.makedirs(RECORDINGS_DIR, exist_ok=True)

print("Starting Playwright demo recording...")

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
    )
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        record_video_dir=RECORDINGS_DIR,
        record_video_size={"width": 1280, "height": 720}
    )
    page = context.new_page()

    print(f"Navigating to {TARGET_URL}...")
    page.goto(TARGET_URL, wait_until="networkidle")
    time.sleep(3)

    # 1. First Prompt: Click sample prompt chip "🌱 List all plants"
    print("Executing Prompt 1: List all plants in catalog...")
    chip = page.locator(".chip:has-text('List all plants')")
    if chip.count() > 0:
        chip.first.click()
    else:
        page.fill("#input", "List all plants in the catalog")
        page.click("form button")

    # Wait for assistant response card
    print("Waiting for assistant response 1...")
    page.wait_for_selector(".msg.agent", timeout=60000)
    time.sleep(6)  # Pause to showcase catalog UI

    # 2. Second Prompt: Richer prompt showing taxonomy lookup & image generation
    rich_prompt = "Lookup plant taxonomy for Monstera deliciosa and generate a fresh visual image for it."
    print(f"Executing Prompt 2: '{rich_prompt}'...")
    page.fill("#input", rich_prompt)
    time.sleep(1)
    page.click("form button")

    # Wait for second assistant turn
    print("Waiting for assistant response 2...")
    time.sleep(5)
    page.wait_for_function(
        "() => document.querySelectorAll('.msg.agent').length >= 2",
        timeout=120000
    )
    time.sleep(8)  # Pause to showcase response and reasoning accordion

    # 3. Interactive features: Click generated image if visible
    try:
        images = page.locator(".bubble img, .a2img")
        if images.count() > 0:
            print("Attempting to click plant image to showcase lightbox...")
            images.last.scroll_into_view_if_needed()
            images.last.click(timeout=5000)
            time.sleep(4)
            page.click("#lightbox", timeout=5000)
            time.sleep(2)
    except Exception as e:
        print(f"Lightbox showcase skipped: {e}")

    # 4. Showcase Dark Mode toggle
    try:
        print("Toggling dark mode...")
        page.click("#theme-btn", timeout=5000)
        time.sleep(4)
    except Exception as e:
        print(f"Dark mode toggle skipped: {e}")

    time.sleep(3)
    video_path = page.video.path()
    context.close()
    browser.close()

print(f"Raw webm recording saved at: {video_path}")

# Convert webm to mp4 using ffmpeg
mp4_path = os.path.join(RECORDINGS_DIR, "demo_recording.mp4")
if os.path.exists(video_path):
    print("Converting video to MP4 format using ffmpeg...")
    cmd = ["ffmpeg", "-i", video_path, "-vcodec", "libx264", "-pix_fmt", "yuv420p", "-y", mp4_path]
    subprocess.run(cmd, check=True)
    print(f"Converted MP4 saved at: {mp4_path}")

# Upload videos to GCS bucket
storage_client = storage.Client(project=FIRESTORE_PROJECT)
bucket = storage_client.bucket(GCS_BUCKET_NAME)

if os.path.exists(mp4_path):
    blob = bucket.blob("demo_recording.mp4")
    blob.upload_from_filename(mp4_path, content_type="video/mp4")
    public_mp4_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/demo_recording.mp4"
    print(f"Uploaded MP4 demo recording to GCS: {public_mp4_url}")

if os.path.exists(video_path):
    blob_webm = bucket.blob("demo_recording.webm")
    blob_webm.upload_from_filename(video_path, content_type="video/webm")
    public_webm_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/demo_recording.webm"
    print(f"Uploaded WebM demo recording to GCS: {public_webm_url}")
