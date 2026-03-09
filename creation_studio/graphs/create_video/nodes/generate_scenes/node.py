import random
import string

from creation_studio.graphs.utils.veo_utils import generate_video_scene
from creation_studio.graphs.utils.cloudinary_utils import upload_video
from .scene_prompt_engineer import build_scene_prompt


def _make_uuid(length: int = 17) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))


def generate_scenes_node(state: dict) -> dict:
    strategy = state.get("video_strategy", {})
    scenes_spec = strategy.get("scenes", [])

    brand_dna = state.get("brand_dna", {})
    identity = state.get("identity", {})
    company = identity.get("name", brand_dna.get("identity", {}).get("name", ""))
    aspect_ratio = state.get("aspect_ratio", "9:16")
    scene_duration = state.get("scene_duration", 6)
    template_context = state.get("template_context", "")
    creation_uuid = state.get("creation_uuid", _make_uuid())

    completed_scenes = []

    for scene in scenes_spec:
        scene_number = scene.get("scene_number", len(completed_scenes) + 1)

        prompt = build_scene_prompt(
            scene=scene,
            brand_dna=brand_dna,
            aspect_ratio=aspect_ratio,
            scene_duration=scene_duration,
            company=company,
            template_context=template_context,
        )

        video_url = ""
        filtered = False
        filter_reason = ""
        error = ""

        try:
            video_b64 = generate_video_scene(
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                duration=scene_duration,
            )
        except Exception as e:
            error = str(e)
            print(f"[video] scene {scene_number} generation failed: {e}")
            video_b64 = None

        if video_b64 is None and not error:
            filtered = True
            filter_reason = "Scene filtered by Veo safety policy"
            print(f"[video] scene {scene_number} filtered by safety")
        elif video_b64:
            generation_uuid = _make_uuid()
            folder = f"ia_generations/{creation_uuid}/video"
            try:
                video_url = upload_video(video_b64, folder, generation_uuid)
            except Exception as e:
                error = f"Cloudinary upload failed: {e}"
                print(f"[video] scene {scene_number} upload failed: {e}")

        scene_result = {
            "scene_number": scene_number,
            "type": scene.get("type", "value"),
            "scene_description": scene.get("scene_description", ""),
            "video_url": video_url,
            "filtered": filtered,
        }
        if filter_reason:
            scene_result["filter_reason"] = filter_reason
        if error:
            scene_result["error"] = error

        completed_scenes.append(scene_result)

    return {"completed_scenes": completed_scenes}
