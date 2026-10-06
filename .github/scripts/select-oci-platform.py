#!/usr/bin/env python3
"""Create a single-platform view of a multi-platform OCI image layout."""

import json
import os
import shutil
import sys
from pathlib import Path


INDEX_TYPES = {
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
}


def image_manifests(layout, index):
    for descriptor in index["manifests"]:
        if descriptor["mediaType"] in INDEX_TYPES:
            algorithm, digest = descriptor["digest"].split(":", 1)
            child = json.loads((layout / "blobs" / algorithm / digest).read_text())
            yield from image_manifests(layout, child)
        else:
            yield descriptor


def main():
    source_arg, platform, destination_arg = sys.argv[1:]
    source, destination = Path(source_arg), Path(destination_arg)
    os_name, architecture = platform.split("/", 1)
    index = json.loads((source / "index.json").read_text())
    matches = [
        descriptor
        for descriptor in image_manifests(source, index)
        if (descriptor.get("platform") or {}).get("os") == os_name
        and (descriptor.get("platform") or {}).get("architecture") == architecture
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one {platform} image, found {len(matches)}")

    destination.mkdir()
    shutil.copyfile(source / "oci-layout", destination / "oci-layout")
    os.symlink((source / "blobs").resolve(), destination / "blobs")
    (destination / "index.json").write_text(
        json.dumps({"schemaVersion": 2, "manifests": matches})
    )


if __name__ == "__main__":
    main()
