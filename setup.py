from setuptools import setup, find_packages

PLUGIN_ENTRY_POINT = (
    "ovos-skill-share-to-mirror.smartgic=ovos_skill_share_to_mirror:ShareToMirrorSkill"
)

setup(
    name="ovos-skill-share-to-mirror",
    version="0.1.5",
    description="Control YouTube playback on MagicMirror via MMM-ShareToMirror",
    author="Smart'Gic",
    license="Apache-2.0",
    url="https://github.com/your-org/ovos-skill-share-to-mirror",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "ovos-workshop>=0.0.16",
        "ovos-utils>=0.0.37",
        "requests>=2.31.0",
        "yt-dlp>=2024.4.9",
        "google-api-python-client>=2.129.0",
        "fuzzywuzzy>=0.18.0"
    ],
    entry_points={"ovos.plugin.skill": [PLUGIN_ENTRY_POINT]},
    python_requires=">=3.8",
)
