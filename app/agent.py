# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
import os
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv
from google import genai
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.cloud import firestore, storage
from google.genai import types

load_dotenv()

# Hardcoded GCP Project ID & Bucket Name & Memory Bank ID
FIRESTORE_PROJECT = "qwiklabs-gcp-01-9657f097aca6"
GCS_BUCKET_NAME = "plant-catalog-assets-9657f097aca6"
MEMORY_BANK_ID = "1658458809116393472"

db = firestore.Client(project=FIRESTORE_PROJECT)
storage_client = storage.Client(project=FIRESTORE_PROJECT)
genai_client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT, location="global")

# Retrieve Agent Engine resource name from deployment_metadata.json
DEPLOYMENT_METADATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "deployment_metadata.json"
)

agent_engine_resource_name = None
if os.path.exists(DEPLOYMENT_METADATA_PATH):
    try:
        with open(DEPLOYMENT_METADATA_PATH, "r") as f:
            meta = json.load(f)
            agent_engine_resource_name = meta.get("remote_agent_runtime_id")
    except Exception:
        pass

code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=agent_engine_resource_name
)


# WRITE: after each turn, extract and send durable memories to Memory Bank
async def generate_memories_callback(callback_context: CallbackContext):
    try:
        if getattr(callback_context, "memory_service", None) is not None:
            await callback_context.add_session_to_memory()
    except Exception as e:
        print(f"Memory update notice: {e}")
    return None


# Memory service builder for Agent Engine Memory Bank
def memory_bank_service_builder():
    return VertexAiMemoryBankService(
        project=FIRESTORE_PROJECT,
        location="us-central1",
        agent_engine_id=MEMORY_BANK_ID,
    )


def get_weather(query: str) -> str:
    """Simulates a web search. Use it get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        city: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


def list_items(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """List items from the catalog in Firestore database.

    Args:
        category: Optional category name to filter items by.

    Returns:
        A list of items matching the query.
    """
    collection_ref = db.collection("items")
    if category:
        query = collection_ref.where("category", "==", category)
        docs = query.stream()
    else:
        docs = collection_ref.stream()

    items = []
    for doc in docs:
        item = doc.to_dict()
        item["id"] = doc.id
        items.append(item)
    return items


def get_item_details(item_id: str) -> Dict[str, Any]:
    """Fetch details of a specific item by its ID from Firestore.

    Args:
        item_id: The document ID of the item.

    Returns:
        A dictionary containing item details, or an error message if not found.
    """
    doc_ref = db.collection("items").document(item_id)
    doc = doc_ref.get()
    if doc.exists:
        item = doc.to_dict()
        item["id"] = doc.id
        return item
    return {"error": f"Item with ID '{item_id}' not found."}


def add_item(name: str, category: str, price: float, stock: int, description: str) -> Dict[str, Any]:
    """Add a new item to the catalog stored in Firestore.

    Args:
        name: Name of the item.
        category: Category of the item.
        price: Price of the item in USD.
        stock: Stock quantity available.
        description: Description of the item.

    Returns:
        The newly created item dictionary.
    """
    item_id = name.lower().replace(" ", "-")
    item_data = {
        "id": item_id,
        "name": name,
        "category": category,
        "price": price,
        "stock": stock,
        "description": description,
    }
    db.collection("items").document(item_id).set(item_data)
    return item_data


def upload_item_image(item_id: str, filename: str, content: str = "sample plant image bytes") -> Dict[str, Any]:
    """Uploads an image file for a plant item to Cloud Storage and updates the Firestore document with its public URL.

    Args:
        item_id: The document ID of the item in Firestore (e.g., 'monstera-deliciosa').
        filename: Name of the image file to store in GCS (e.g., 'monstera.jpg').
        content: The raw text or image content to store in GCS.

    Returns:
        A dictionary containing the item ID and public GCS image URL.
    """
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(content, content_type="image/jpeg")
    public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"

    doc_ref = db.collection("items").document(item_id)
    if doc_ref.get().exists:
        doc_ref.update({"image_url": public_url})

    return {
        "item_id": item_id,
        "image_url": public_url,
        "status": f"Successfully uploaded {filename} to GCS and updated Firestore item '{item_id}'."
    }


def lookup_plant_taxonomy(plant_name: str) -> Dict[str, Any]:
    """Fetches real botanical taxonomy information for a plant species from the GBIF (Global Biodiversity Information Facility) API.

    Args:
        plant_name: The common or scientific name of the plant species (e.g. 'Monstera deliciosa' or 'Ficus elastica').

    Returns:
        A dictionary containing botanical classification data including scientific name, family, genus, and order.
    """
    api_key = os.environ.get("GBIF_API_KEY", "")
    encoded_name = urllib.parse.quote(plant_name)
    url = f"https://api.gbif.org/v1/species/match?name={encoded_name}"
    headers = {"User-Agent": "PlantCatalogAgent/1.0"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            return {
                "searched_name": plant_name,
                "scientific_name": data.get("scientificName", "Unknown"),
                "canonical_name": data.get("canonicalName", "Unknown"),
                "family": data.get("family", "Unknown"),
                "genus": data.get("genus", "Unknown"),
                "order": data.get("order", "Unknown"),
                "kingdom": data.get("kingdom", "Plantae"),
                "match_status": data.get("status", "Unknown"),
                "confidence": data.get("confidence", 0),
            }
    except Exception as e:
        return {"error": f"Failed to fetch plant taxonomy for '{plant_name}': {str(e)}"}


def geocode_address(address: str) -> Dict[str, Any]:
    """Converts a street address or location name into geographic coordinates using the Google Maps Geocoding API.

    Args:
        address: The address or location to geocode (e.g., '1600 Amphitheatre Pkwy, Mountain View, CA').

    Returns:
        A dictionary containing the formatted name, address, and location coordinates (latitude and longitude).
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY environment variable is not set."}

    encoded_addr = urllib.parse.quote(address)
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_addr}&key={api_key}"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            if data.get("status") == "OK" and data.get("results"):
                result = data["results"][0]
                return {
                    "name": result.get("formatted_address"),
                    "address": result.get("formatted_address"),
                    "location": {
                        "latitude": result["geometry"]["location"]["lat"],
                        "longitude": result["geometry"]["location"]["lng"],
                    },
                }
            return {"error": f"Geocoding failed for address '{address}': {data.get('status')}"}
    except Exception as e:
        return {"error": f"Geocoding API error: {str(e)}"}


def find_nearby_places(latitude: float, longitude: float, place_type: str = "florist", radius_meters: float = 5000.0) -> Dict[str, Any]:
    """Finds nearby places of a given type around a location using the Google Places API (New).

    Args:
        latitude: Latitude coordinate of the center location.
        longitude: Longitude coordinate of the center location.
        place_type: Type of place to search for (e.g. 'florist', 'park', 'store').
        radius_meters: Search radius in meters (default 5000.0).

    Returns:
        A dictionary containing a list of nearby places with key fields (name, address, location).
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY environment variable is not set."}

    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
    }
    body = json.dumps({
        "includedTypes": [place_type],
        "locationRestriction": {
            "circle": {
                "center": {"latitude": latitude, "longitude": longitude},
                "radius": float(radius_meters),
            }
        },
    }).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            raw_places = data.get("places", [])
            places = []
            for item in raw_places:
                places.append({
                    "name": item.get("displayName", {}).get("text", "Unknown"),
                    "address": item.get("formattedAddress", "Unknown"),
                    "location": item.get("location", {}),
                })
            return {"places": places, "count": len(places)}
    except Exception as e:
        return {"error": f"Places API error: {str(e)}"}


def generate_item_image(prompt: str, item_id: str, tool_context: Optional[ToolContext] = None) -> Dict[str, Any]:
    """Generates an image for a plant catalog item using gemini-3.1-flash-lite-image model in global region. Saves it as an artifact and uploads image bytes to Cloud Storage.

    Args:
        prompt: Detailed visual prompt describing the plant image to generate (e.g. 'A lush Monstera deliciosa plant in a ceramic pot').
        item_id: Document ID of the item in Firestore (e.g. 'monstera-deliciosa').

    Returns:
        A dictionary containing the item ID and public GCS image URL.
    """
    response = genai_client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"]
        ),
    )

    img_bytes = None
    mime_type = "image/jpeg"
    if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                img_bytes = part.inline_data.data
                if part.inline_data.mime_type:
                    mime_type = part.inline_data.mime_type
                break

    if not img_bytes:
        return {"error": "Failed to generate image bytes from model."}

    filename = f"{item_id}.jpg"

    # 1. Save artifact to Playground's Artifacts panel if tool_context is provided
    if tool_context:
        artifact_part = types.Part.from_bytes(data=img_bytes, mime_type=mime_type)
        tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload image bytes directly to GCS bucket (without writing to local file)
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(img_bytes, content_type=mime_type)
    public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"

    # Update Firestore item document with public image_url if document exists
    doc_ref = db.collection("items").document(item_id)
    if doc_ref.get().exists:
        doc_ref.update({"image_url": public_url})

    return {
        "item_id": item_id,
        "image_url": public_url,
        "status": f"Successfully generated image, saved artifact '{filename}', and uploaded to GCS."
    }


def generate_item_video(prompt: str, item_id: str, tool_context: Optional[ToolContext] = None) -> Dict[str, Any]:
    """Generates a short video for a plant catalog item using Google's Omni model (gemini-omni-flash-preview) in global region. Saves it as an artifact and uploads video bytes to Cloud Storage.

    Args:
        prompt: Detailed visual prompt describing the plant video to generate (e.g. 'A smooth timelapse of a Monstera leaf unfurling').
        item_id: Document ID of the item in Firestore (e.g. 'monstera-deliciosa').

    Returns:
        A dictionary containing the item ID and public GCS video URL.
    """
    import base64

    response = genai_client.interactions.create(
        model="gemini-omni-flash-preview",
        input=prompt,
        response_modalities=["text", "video"],
    )

    video_bytes = None
    mime_type = "video/mp4"

    if hasattr(response, "output_video") and response.output_video:
        data = response.output_video.data
        if data:
            if isinstance(data, str):
                video_bytes = base64.b64decode(data)
            else:
                video_bytes = data
            if getattr(response.output_video, "mime_type", None):
                mime_type = response.output_video.mime_type

    if not video_bytes:
        return {"error": "Failed to generate video bytes from gemini-omni-flash-preview model."}

    filename = f"{item_id}.mp4"

    # 1. Save artifact to Playground's Artifacts panel if tool_context is provided
    if tool_context:
        artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
        tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload video bytes directly to GCS bucket (without writing to local file)
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(video_bytes, content_type=mime_type)
    public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"

    # Update Firestore item document with public video_url if document exists
    doc_ref = db.collection("items").document(item_id)
    if doc_ref.get().exists:
        doc_ref.update({"video_url": public_url})

    return {
        "item_id": item_id,
        "video_url": public_url,
        "status": f"Successfully generated video using gemini-omni-flash-preview, saved artifact '{filename}', and uploaded to GCS."
    }


from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from .a2ui_utils import a2ui_callback

schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = schema_manager.generate_system_prompt(
    role_description="Plant Catalog AI assistant designed to provide accurate and useful information. You remember all user preferences, health requirements, and allergies (such as plant, pollen, food, or chemical allergies) across conversations, and use them to personalize responses and warn the user about potential allergens.",
    workflow_description="Analyze the user request, use available tools (weather, time, Firestore product catalog, GBIF taxonomy, Google Maps & Places, image generation, video generation, python sandbox), and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=a2ui_instruction,
    tools=[
        PreloadMemoryTool(),
        get_weather,
        get_current_time,
        list_items,
        get_item_details,
        add_item,
        upload_item_image,
        lookup_plant_taxonomy,
        geocode_address,
        find_nearby_places,
        generate_item_image,
        generate_item_video,
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
    code_executor=code_executor,
)

app = App(
    root_agent=root_agent,
    name="app",
)







