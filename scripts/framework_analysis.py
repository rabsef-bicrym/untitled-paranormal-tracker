#!/usr/bin/env python3
"""
Framework analysis for paranormal stories using Anthropic.

Produces strict JSON output for multiple parapsychology frameworks.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any

import requests


DEFAULT_ANTHROPIC_MODEL = "claude-3-haiku-20240307"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
FRAMEWORK_SCHEMA_VERSION = "2026-01-26.3"

BELIEF_STANCES = {"affirmed", "denied", "not_mentioned"}

FRAMEWORKS = {
    "caps": [
        "temporal_lobe",
        "clinical_perceptual",
        "chemosensory",
        "sleep_related",
        "external_agent",
    ],
    "sleep_paralysis": [
        "intruder",
        "incubus",
        "vestibular_motor",
    ],
    "hypnagogic": [
        "visual",
        "auditory",
        "tactile",
        "proprioceptive",
    ],
    "aei": [
        "experience",
        "belief",
        "ability",
        "fear",
        "drug_use",
    ],
    "rpbs": [
        "traditional_religious_belief",
        "psi",
        "witchcraft",
        "superstition",
        "spiritualism",
        "extraordinary_life_forms",
        "precognition",
    ],
    "lshs_r": [
        "auditory_hallucination_like",
        "visual_hallucination_like",
        "vivid_mental_events",
        "intrusive_thoughts",
        "sensed_presence",
        "dissociation_like",
    ],
}

CATEGORY_GUIDANCE = {
    "caps": {
        "temporal_lobe": "time distortion, deja vu, precognition, sensed presence, altered time flow",
        "clinical_perceptual": "hallucination-like perceptions (voices, figures, sounds) without a clear source",
        "chemosensory": "smells or tastes without an external source",
        "sleep_related": "experiences at sleep onset/waking, sleep paralysis, hypnagogic/hypnopompic states",
        "external_agent": "perceived external entity or force (apparition, alien, possession, haunting)",
    },
    "sleep_paralysis": {
        "intruder": "sense of a nearby presence, footsteps, someone in the room",
        "incubus": "pressure on chest, suffocation, assault-like sensations",
        "vestibular_motor": "floating, flying, out-of-body, movement illusions",
    },
    "hypnagogic": {
        "visual": "visual imagery during sleep-wake transition",
        "auditory": "sounds/voices during sleep-wake transition",
        "tactile": "touch/pressure during sleep-wake transition",
        "proprioceptive": "body/position distortions during sleep-wake transition",
    },
    "aei": {
        "experience": "explicit anomalous experience described",
        "belief": "explicit belief or disbelief statements about the paranormal",
        "ability": "claims of psychic or anomalous abilities",
        "fear": "explicit fear, dread, terror tied to the event",
        "drug_use": "explicit mention of drugs/alcohol affecting experience",
    },
    "rpbs": {
        "traditional_religious_belief": "God, angels, demons, heaven/hell, religious doctrine",
        "psi": "telepathy, clairvoyance, telekinesis, mind-over-matter",
        "witchcraft": "spells, magic rituals, curses",
        "superstition": "omens, bad luck, lucky objects",
        "spiritualism": "communication with spirits, mediums, séances",
        "extraordinary_life_forms": "aliens, cryptids, non-human beings",
        "precognition": "knowledge of future events, prophetic dreams",
    },
    "lshs_r": {
        "auditory_hallucination_like": "hearing voices/sounds with no clear source",
        "visual_hallucination_like": "seeing figures/lights/shapes with no clear source",
        "vivid_mental_events": "vivid imagery mistaken as real",
        "intrusive_thoughts": "thoughts or images that feel inserted or uncontrolled",
        "sensed_presence": "feeling a presence without direct sensory evidence",
        "dissociation_like": "depersonalization/derealization, feeling detached from self/world",
    },
}


@dataclass
class FrameworkResult:
    frameworks: dict[str, Any]
    model: str
    schema_version: str = FRAMEWORK_SCHEMA_VERSION

    def to_json(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "model": self.model,
            "frameworks": self.frameworks,
        }


def _build_output_template() -> dict[str, Any]:
    def present_template():
        return {"present": False}

    def belief_template():
        return {"stance": "not_mentioned"}

    output = {}
    for fw, keys in FRAMEWORKS.items():
        output[fw] = {}
        for key in keys:
            if fw == "rpbs" or (fw == "aei" and key == "belief"):
                output[fw][key] = belief_template()
            else:
                output[fw][key] = present_template()
    return output


def build_framework_prompt(story_text: str) -> str:
    guidance_lines = []
    for fw, keys in FRAMEWORKS.items():
        guidance_lines.append(f"{fw}:")
        for key in keys:
            desc = CATEGORY_GUIDANCE.get(fw, {}).get(key, "no description")
            guidance_lines.append(f"  - {key}: {desc}")
    guidance = "\n".join(guidance_lines)
    required_lines = []
    for fw, keys in FRAMEWORKS.items():
        required_lines.append(f"{fw}: {', '.join(keys)}")
    required_fields = "\n".join(required_lines)
    return (
        "Task: Analyze the story under multiple parapsychology frameworks.\n"
        "Return your analysis by calling the provided tool.\n\n"
        "Category guidance:\n"
        f"{guidance}\n\n"
        "Required fields (all must be present):\n"
        f"{required_fields}\n\n"
        "Rules:\n"
        "- For non-belief fields: set present=true ONLY if explicitly stated.\n"
        "- For belief fields (RPBS dimensions and AEI belief):\n"
        "  stance MUST be one of: affirmed, denied, not_mentioned.\n"
        "  Do NOT infer belief. Only mark affirmed/denied if explicitly stated.\n"
        "- If unsure or not mentioned, set present=false or stance=not_mentioned.\n"
        "- You MUST fill every field; do not omit anything.\n\n"
        "Story:\n"
        "<<<\n"
        f"{story_text}\n"
        ">>>\n"
    )


def _validate_frameworks(data: dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise ValueError("Framework output is not an object")

    for fw, keys in FRAMEWORKS.items():
        if fw not in data:
            raise ValueError(f"Missing framework: {fw}")
        if not isinstance(data[fw], dict):
            raise ValueError(f"Framework {fw} is not an object")

        for key in keys:
            if key not in data[fw]:
                raise ValueError(f"Missing {fw}.{key}")
            entry = data[fw][key]
            if not isinstance(entry, dict):
                raise ValueError(f"{fw}.{key} is not an object")

            if fw == "rpbs" or (fw == "aei" and key == "belief"):
                stance = entry.get("stance")
                if stance not in BELIEF_STANCES:
                    raise ValueError(f"{fw}.{key}.stance invalid: {stance}")
            else:
                if "present" not in entry or not isinstance(entry["present"], bool):
                    raise ValueError(f"{fw}.{key}.present invalid or missing")


def _build_tool_schema() -> dict[str, Any]:
    def present_schema() -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "present": {"type": "boolean"},
            },
            "required": ["present"],
            "additionalProperties": False,
        }

    def belief_schema() -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "stance": {"type": "string", "enum": sorted(BELIEF_STANCES)},
            },
            "required": ["stance"],
            "additionalProperties": False,
        }

    frameworks_schema: dict[str, Any] = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}
    for fw, keys in FRAMEWORKS.items():
        fw_props: dict[str, Any] = {}
        for key in keys:
            if fw == "rpbs" or (fw == "aei" and key == "belief"):
                fw_props[key] = belief_schema()
            else:
                fw_props[key] = present_schema()
        frameworks_schema["properties"][fw] = {
            "type": "object",
            "properties": fw_props,
            "required": keys,
            "additionalProperties": False,
        }
        frameworks_schema["required"].append(fw)

    return {
        "type": "object",
        "properties": {
            "frameworks": frameworks_schema,
        },
        "required": ["frameworks"],
        "additionalProperties": False,
    }


def _call_anthropic(prompt: str, api_key: str, model: str, max_tokens: int = 3000) -> dict[str, Any]:
    tool_schema = _build_tool_schema()
    response = requests.post(
        ANTHROPIC_API_URL,
        headers={
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": max_tokens,
            "temperature": 0,
            "messages": [{"role": "user", "content": prompt}],
            "tools": [
                {
                    "name": "framework_analysis",
                    "description": "Return the framework analysis for the story.",
                    "input_schema": tool_schema,
                }
            ],
            "tool_choice": {"type": "tool", "name": "framework_analysis"},
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    for block in payload.get("content", []):
        if block.get("type") == "tool_use" and block.get("name") == "framework_analysis":
            return block.get("input", {})
    raise ValueError("No tool_use response found from model")


def analyze_story_frameworks(
    story_text: str,
    api_key: str,
    model: str | None = None,
    max_retries: int = 2,
) -> FrameworkResult:
    model_name = model or os.environ.get("ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL)
    base_prompt = build_framework_prompt(story_text)

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        if attempt > 0:
            time.sleep(1.5 * attempt)

        try:
            if attempt == 0:
                prompt = base_prompt
            else:
                prompt = (
                    base_prompt
                    + "\nIMPORTANT: Your previous tool call was incomplete or invalid. "
                      "You must call the tool with ALL required fields, using defaults when unknown."
                )
            parsed = _call_anthropic(prompt, api_key, model_name)
            if not isinstance(parsed, dict):
                raise ValueError(f"Tool input not an object: {parsed!r}")
            frameworks = parsed.get("frameworks")
            if frameworks is None:
                raise ValueError(f"Tool input missing 'frameworks': {parsed!r}")
            _validate_frameworks(frameworks)
            return FrameworkResult(frameworks=frameworks, model=model_name)
        except Exception as exc:
            last_error = exc

    raise RuntimeError(f"Framework analysis failed after {max_retries + 1} attempts: {last_error}")
