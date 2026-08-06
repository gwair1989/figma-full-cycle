#!/bin/zsh

set -u
set -o pipefail

usage() {
    /usr/bin/printf '%s\n' \
        "Usage: generate_xcode_imageset.zsh --input FILE --catalog Assets.xcassets [--group RELATIVE/PATH] [--name NAME] [--rendering-intent default|original|template] [--replace]"
}

die() {
    /usr/bin/printf 'error: %s\n' "$1" >&2
    exit "${2:-1}"
}

input=""
catalog=""
group=""
asset_name=""
rendering_intent="default"
rendering_intent_explicit=0
replace=0

while (( $# > 0 )); do
    case "$1" in
        --input)
            (( $# >= 2 )) || die "--input requires a value" 2
            input="$2"
            shift 2
            ;;
        --catalog)
            (( $# >= 2 )) || die "--catalog requires a value" 2
            catalog="$2"
            shift 2
            ;;
        --group)
            (( $# >= 2 )) || die "--group requires a value" 2
            group="$2"
            shift 2
            ;;
        --name)
            (( $# >= 2 )) || die "--name requires a value" 2
            asset_name="$2"
            shift 2
            ;;
        --rendering-intent)
            (( $# >= 2 )) || die "--rendering-intent requires a value" 2
            rendering_intent="$2"
            rendering_intent_explicit=1
            shift 2
            ;;
        --replace)
            replace=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            die "unknown argument: $1" 2
            ;;
    esac
done

[[ -n "$input" ]] || die "missing --input" 2
[[ -n "$catalog" ]] || die "missing --catalog" 2
[[ "$rendering_intent" == "default" || "$rendering_intent" == "original" || "$rendering_intent" == "template" ]] || \
    die "--rendering-intent must be default, original, or template" 2
[[ -f "$input" ]] || die "input file does not exist: $input" 2
[[ -d "$catalog" ]] || die "asset catalog does not exist: $catalog" 2
[[ "${catalog:t}" == *.xcassets ]] || die "--catalog must point to an existing .xcassets directory" 2
[[ -x /usr/bin/python3 ]] || die "/usr/bin/python3 is required; install Xcode Command Line Tools" 2

input="${input:A}"
catalog="${catalog:A}"
script_dir="${0:A:h}"
destination="$catalog"
if [[ -n "$group" ]]; then
    /usr/bin/python3 - "$group" <<'PY' || die "--group must be a safe relative path without empty, dot, or parent components" 2
import sys

group = sys.argv[1]
parts = group.split("/")
if group.startswith("/") or "\\" in group or any(part in ("", ".", "..") for part in parts):
    raise SystemExit(1)
PY
    [[ -d "$catalog/$group" ]] || die "asset catalog group does not exist: $group" 2
    destination="$catalog/$group"
    destination="${destination:A}"
    [[ "$destination" == "$catalog"/* ]] || die "asset catalog group resolves outside the catalog" 2
fi
filename="${input:t}"
stem="${filename:r}"
extension="${filename:e:l}"

case "$extension" in
    png|svg|pdf) ;;
    *) die "supported inputs are PNG, SVG, and PDF" 2 ;;
esac

case "$extension" in
    png)
        [[ -x /usr/bin/sips ]] || die "/usr/bin/sips is required for PNG input" 2
        detected_format=$(/usr/bin/sips -g format "$input" 2>/dev/null |
            /usr/bin/awk '/format:/ { print $2 }')
        [[ "$detected_format" == "png" ]] || die "file content does not match its .png extension" 2
        ;;
    svg)
        /usr/bin/python3 - "$input" <<'PY' || die "file content is not a valid SVG document" 2
import sys
import xml.etree.ElementTree as ET

root = ET.parse(sys.argv[1]).getroot()
if root.tag.rsplit("}", 1)[-1].lower() != "svg":
    raise SystemExit(1)
PY
        ;;
    pdf)
        pdf_header=$(/usr/bin/head -c 5 "$input" 2>/dev/null)
        [[ "$pdf_header" == "%PDF-" ]] || die "file content does not match its .pdf extension" 2
        ;;
esac

if [[ "$extension" == "png" && ( "$stem" == *@1[xX] || "$stem" == *@2[xX] ) ]]; then
    die "PNG input must be the 3x source, not a file named @1x or @2x" 2
fi

if [[ -z "$asset_name" ]]; then
    asset_name="${stem%@3x}"
    asset_name="${asset_name%@3X}"
fi
asset_name="${asset_name%.imageset}"

[[ -n "$asset_name" && "$asset_name" != "." && "$asset_name" != ".." ]] || die "asset name is empty or invalid" 2
[[ "$asset_name" != */* && "$asset_name" != *\\* && "$asset_name" != *$'\n'* && "$asset_name" != *$'\r'* ]] || \
    die "asset name must not contain path separators or line breaks" 2

target="$destination/$asset_name.imageset"
if [[ -e "$target" && ! -d "$target" ]]; then
    die "target exists and is not an image set directory: $target" 3
fi
if [[ -e "$target" && "$replace" -ne 1 ]]; then
    die "image set already exists; inspect it and pass --replace to replace it: $target" 3
fi
if [[ -e "$target" && "$replace" -eq 1 ]]; then
    existing_intent=$(
        /usr/bin/python3 - "$target/Contents.json" "$target" <<'PY'
import json
import os
import sys

manifest_path, root = sys.argv[1:]
with open(manifest_path, encoding="utf-8") as file:
    payload = json.load(file)

if payload.get("info") != {"author": "xcode", "version": 1}:
    raise SystemExit(1)
images = payload.get("images")
if not isinstance(images, list):
    raise SystemExit(1)
if any(not isinstance(image, dict) or set(image) != {"filename", "idiom", "scale"} for image in images):
    raise SystemExit(1)
if any(image.get("idiom") != "universal" for image in images):
    raise SystemExit(1)
filenames = [image.get("filename") for image in images]
if any(not isinstance(filename, str) or os.path.basename(filename) != filename for filename in filenames):
    raise SystemExit(1)
if any(not os.path.isfile(os.path.join(root, filename)) for filename in filenames):
    raise SystemExit(1)
expected_files = {"Contents.json", *filenames}
actual_files = set(os.listdir(root)) - {".DS_Store"}
if actual_files != expected_files:
    raise SystemExit(1)

scales = [image.get("scale") for image in images]
top_keys = set(payload)
properties = payload.get("properties", {})
intent = properties.get("template-rendering-intent", "default")
if intent not in {"default", "original", "template"}:
    raise SystemExit(1)
intent_properties = {} if intent == "default" else {"template-rendering-intent": intent}
expected_top_keys = {"images", "info"} | ({"properties"} if properties else set())
is_plain_raster = (
    scales == ["1x", "2x", "3x"]
    and top_keys == expected_top_keys
    and properties == intent_properties
)
is_plain_vector = (
    scales == ["1x"]
    and top_keys == {"images", "info", "properties"}
    and properties == {"preserves-vector-representation": True, **intent_properties}
)
if not (is_plain_raster or is_plain_vector):
    raise SystemExit(1)
print(intent)
PY
    ) || die "existing image set contains unsupported variants, metadata, or untracked files; refusing destructive replacement" 3
    if (( ! rendering_intent_explicit )) && [[ "$existing_intent" != "default" ]]; then
        rendering_intent="$existing_intent"
    fi
fi

temp_dir=$(/usr/bin/mktemp -d "$destination/.$asset_name.imageset.tmp.XXXXXX" 2>/dev/null) || \
    die "cannot create a temporary directory beside the target image set" 4
backup_dir=""
backup_holds_original=0

safe_remove_tree() {
    local candidate="$1"
    [[ -n "$candidate" && "$candidate" == "$destination"/.* ]] || return 1
    /bin/rm -rf -- "$candidate"
}

cleanup() {
    local original_exit=$?
    if (( backup_holds_original )) && [[ -n "$backup_dir" && -e "$backup_dir" && ! -e "$target" ]]; then
        if /bin/mv "$backup_dir" "$target" >/dev/null 2>&1; then
            backup_holds_original=0
            backup_dir=""
            /usr/bin/printf 'warning: restored the existing image set after an interrupted replacement\n' >&2
        else
            /usr/bin/printf 'error: could not restore the existing image set; recovery copy remains at %s\n' "$backup_dir" >&2
        fi
    elif (( backup_holds_original )) && [[ -n "$backup_dir" && -e "$backup_dir" ]]; then
        /usr/bin/printf 'warning: replacement backup remains at %s\n' "$backup_dir" >&2
    fi
    if [[ -n "$temp_dir" && -d "$temp_dir" ]]; then
        safe_remove_tree "$temp_dir" >/dev/null 2>&1 || true
    fi
    return "$original_exit"
}

trap cleanup EXIT
trap 'exit 130' HUP INT TERM

has_size() {
    local file="$1"
    local expected_width="$2"
    local expected_height="$3"
    local actual_width actual_height

    actual_width=$(/usr/bin/sips -g pixelWidth "$file" 2>/dev/null |
        /usr/bin/awk '/pixelWidth:/ { print $2 }')
    actual_height=$(/usr/bin/sips -g pixelHeight "$file" 2>/dev/null |
        /usr/bin/awk '/pixelHeight:/ { print $2 }')

    [[ "$actual_width" == "$expected_width" && "$actual_height" == "$expected_height" ]]
}

write_contents() {
    local mode="$1"
    shift
    /usr/bin/python3 - "$temp_dir/Contents.json" "$mode" "$rendering_intent" "$@" <<'PY'
import json
import sys

path, mode, rendering_intent, *filenames = sys.argv[1:]
intent_properties = (
    {} if rendering_intent == "default"
    else {"template-rendering-intent": rendering_intent}
)
if mode == "raster":
    scales = ("1x", "2x", "3x")
    images = [
        {"filename": filename, "idiom": "universal", "scale": scale}
        for filename, scale in zip(filenames, scales)
    ]
    payload = {"images": images, "info": {"author": "xcode", "version": 1}}
    if intent_properties:
        payload["properties"] = intent_properties
elif mode == "vector":
    payload = {
        "images": [{"filename": filenames[0], "idiom": "universal", "scale": "1x"}],
        "info": {"author": "xcode", "version": 1},
        "properties": {"preserves-vector-representation": True, **intent_properties},
    }
else:
    raise SystemExit(f"unsupported mode: {mode}")

with open(path, "w", encoding="utf-8", newline="\n") as file:
    json.dump(payload, file, ensure_ascii=False, indent=2)
    file.write("\n")
PY
}

validate_contents() {
    local mode="$1"
    /usr/bin/python3 - "$temp_dir/Contents.json" "$temp_dir" "$mode" "$rendering_intent" <<'PY'
import json
import os
import sys

path, root, mode, rendering_intent = sys.argv[1:]
with open(path, encoding="utf-8") as file:
    payload = json.load(file)

if payload.get("info") != {"author": "xcode", "version": 1}:
    raise SystemExit("invalid info dictionary")
images = payload.get("images")
if not isinstance(images, list) or not images:
    raise SystemExit("missing images")
filenames = []
for image in images:
    filename = image.get("filename")
    if not isinstance(filename, str) or not filename or os.path.basename(filename) != filename:
        raise SystemExit("invalid image filename")
    if not os.path.isfile(os.path.join(root, filename)):
        raise SystemExit(f"missing image file: {filename}")
    if image.get("idiom") != "universal":
        raise SystemExit("invalid image idiom")
    filenames.append(filename)

if set(os.listdir(root)) != {"Contents.json", *filenames}:
    raise SystemExit("unexpected generated files")

scales = [image.get("scale") for image in images]
intent_properties = (
    {} if rendering_intent == "default"
    else {"template-rendering-intent": rendering_intent}
)
if mode == "raster":
    if scales != ["1x", "2x", "3x"]:
        raise SystemExit("invalid raster scales")
    if payload.get("properties", {}) != intent_properties:
        raise SystemExit("invalid raster properties")
if mode == "vector":
    if scales != ["1x"]:
        raise SystemExit("invalid vector scale")
    if payload.get("properties") != {"preserves-vector-representation": True, **intent_properties}:
        raise SystemExit("invalid vector properties")
PY
}

mode=""
detail=""

if [[ "$extension" == "png" ]]; then
    [[ -x /usr/bin/sips ]] || die "/usr/bin/sips is required for PNG input" 2

    width=$(/usr/bin/sips -g pixelWidth "$input" 2>/dev/null |
        /usr/bin/awk '/pixelWidth:/ { print $2 }')
    height=$(/usr/bin/sips -g pixelHeight "$input" 2>/dev/null |
        /usr/bin/awk '/pixelHeight:/ { print $2 }')

    if [[ "$width" != <-> || "$height" != <-> ]] || (( width < 3 || height < 3 )); then
        die "input is not a readable PNG with dimensions of at least 3x3 pixels" 5
    fi

    width_3x=$(( ((width + 1) / 3) * 3 ))
    height_3x=$(( ((height + 1) / 3) * 3 ))
    width_2x=$(( width_3x * 2 / 3 ))
    height_2x=$(( height_3x * 2 / 3 ))
    width_1x=$(( width_3x / 3 ))
    height_1x=$(( height_3x / 3 ))

    file_1x="$asset_name.png"
    file_2x="$asset_name@2x.png"
    file_3x="$asset_name@3x.png"
    path_1x="$temp_dir/$file_1x"
    path_2x="$temp_dir/$file_2x"
    path_3x="$temp_dir/$file_3x"

    if (( width_3x == width && height_3x == height )); then
        /bin/cp -p "$input" "$path_3x" || die "failed to copy the 3x PNG" 5
        detail="source=${width}x${height}; normalized=no"
    else
        normalizer="$script_dir/normalize_png_canvas.swift"
        [[ -f "$normalizer" && -x /usr/bin/xcrun ]] || \
            die "the bundled PNG canvas normalizer or Xcode toolchain is unavailable" 5
        /usr/bin/xcrun --sdk macosx swift \
            "$normalizer" "$input" "$path_3x" "$width_3x" "$height_3x" >/dev/null || \
            die "failed to normalize the 3x PNG canvas" 5
        detail="source=${width}x${height}; canvas=${width_3x}x${height_3x}"
    fi

    /usr/bin/sips \
        --resampleHeightWidth "$height_2x" "$width_2x" \
        "$path_3x" --out "$path_2x" >/dev/null 2>&1 || \
        die "failed to generate the 2x PNG" 5
    /usr/bin/sips \
        --resampleHeightWidth "$height_1x" "$width_1x" \
        "$path_3x" --out "$path_1x" >/dev/null 2>&1 || \
        die "failed to generate the 1x PNG" 5

    has_size "$path_3x" "$width_3x" "$height_3x" || die "3x PNG validation failed" 5
    has_size "$path_2x" "$width_2x" "$height_2x" || die "2x PNG validation failed" 5
    has_size "$path_1x" "$width_1x" "$height_1x" || die "1x PNG validation failed" 5
    write_contents raster "$file_1x" "$file_2x" "$file_3x" || die "failed to write Contents.json" 5
    mode="raster"
else
    vector_file="$asset_name.$extension"
    /bin/cp -p "$input" "$temp_dir/$vector_file" || die "failed to copy the vector asset" 5
    write_contents vector "$vector_file" || die "failed to write Contents.json" 5
    mode="vector"
    detail="format=$extension"
fi

validate_contents "$mode" >/dev/null || die "Contents.json validation failed" 5

action="created"
if [[ -e "$target" ]]; then
    action="replaced"
    backup_dir=$(/usr/bin/mktemp -d "$destination/.$asset_name.imageset.backup.XXXXXX" 2>/dev/null) || \
        die "cannot create a replacement backup" 6
    /bin/rmdir "$backup_dir" || die "cannot prepare the replacement backup" 6
    backup_holds_original=1
    /bin/mv "$target" "$backup_dir" || die "cannot move the existing image set aside" 6
    if ! /bin/mv "$temp_dir" "$target"; then
        if /bin/mv "$backup_dir" "$target" >/dev/null 2>&1; then
            backup_holds_original=0
            backup_dir=""
            die "cannot install the new image set; restored the existing one" 6
        fi
        /usr/bin/printf 'error: automatic restore failed; recovery copy remains at %s\n' "$backup_dir" >&2
        die "cannot install the new image set" 6
    fi
    temp_dir=""
    if safe_remove_tree "$backup_dir"; then
        backup_holds_original=0
        backup_dir=""
    else
        /usr/bin/printf 'warning: replacement backup remains at %s\n' "$backup_dir" >&2
    fi
else
    /bin/mv "$temp_dir" "$target" || die "cannot install the image set" 6
    temp_dir=""
fi

/usr/bin/printf '%s: %s (%s; %s)\n' "$action" "$target" "$mode" "$detail"
