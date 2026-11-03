# WordPress MCP Server

A Model Context Protocol (MCP) server for managing WordPress sites via the REST API. This server provides 20 tools for managing posts, users, media, categories, tags, and site settings.

## Features

### Posts Management (5 tools)
- **list_posts**: List posts with filtering options (status, date, author, categories, tags)
- **retrieve_post**: Get detailed information about a specific post
- **create_post**: Create new posts with full metadata support
- **update_post**: Update existing posts with selective field updates
- **delete_post**: Delete posts (with trash/permanent delete options)

### Users Management (3 tools)
- **list_users**: List site users (admin permission required)
- **get_me**: Get current user information and capabilities
- **validate_credential**: Test WordPress authentication

### Media Management (3 tools)
- **list_media**: List media files with filtering options
- **update_media**: Update media metadata (title, slug, author)
- **delete_media**: Delete media files

### Categories Management (4 tools)
- **list_categories**: List categories with search and filtering
- **create_category**: Create new categories with hierarchy support
- **update_category**: Update existing category information
- **delete_category**: Remove categories

### Tags Management (4 tools)
- **list_tags**: List tags with search and filtering
- **create_tag**: Create new tags
- **update_tag**: Update existing tag information
- **delete_tag**: Remove tags

### Site Management (1 tool)
- **get_site_settings**: Get WordPress site settings (admin required)

## Prerequisites

### WordPress Site Requirements
1. **WordPress.com sites are NOT supported** - only self-hosted WordPress sites (TODO: verify this)
2. **Permalinks must be configured** - go to Settings > Permalinks and choose any structure other than "Plain"
3. **Application Password required** - regular WordPress passwords won't work

### Setting up Application Password
1. Go to your WordPress admin dashboard
2. Navigate to Users > Your Profile
3. Scroll to "Application Passwords" section
4. Click "Add New Application Password"
5. Give it a name (e.g., "MCP Server") and click "Add New Application Password"
6. Copy the generated password - you'll need this for the `WORDPRESS_PASSWORD` environment variable

## Installation

1. Clone or download this project
2. Install dependencies using uv:
```bash
uv sync
```

## Environment Variables

- `WORDPRESS_SITE`: The full URL to your WordPress site (with https:// or http://)
- `WORDPRESS_USERNAME`: Your WordPress username (not email)
- `WORDPRESS_PASSWORD`: The application password you created (NOT your regular WordPress password)

## Usage

### Running the MCP Server

```bash
uv run python main.py
```

This runs FastMCP over stdio.

### Running the container

The container uses [mmmcp](https://github.com/obot-platform/mmmcp) to expose the
same tools over Streamable HTTP at `http://localhost:8099/`.
Export the three WordPress environment variables above, then run:

```bash
docker build -t wordpress-mcp .
docker run --rm -p 127.0.0.1:8099:8099 \
  -e WORDPRESS_SITE -e WORDPRESS_USERNAME -e WORDPRESS_PASSWORD \
  wordpress-mcp
```

Python dependencies are installed from `uv.lock` during the image build;
starting the container does not download dependencies. The container runs as
UID/GID `1000:1000`. mmmcp stores its SQLite event database in
`/var/lib/mmmcp`, which must remain writable. Mount a named volume there if
event storage should persist across container replacements.

`/healthz` checks liveness and `/readyz` checks the MCP catalog and event store.
These probes do not validate WordPress credentials; use `validate_credential`
for that. Existing MCP sessions reconnect when the container is replaced.

## Development

Run the unit test and, optionally, the container integration suite:

```bash
uv sync --frozen
uv run --frozen python -m unittest discover -s tests -v
docker build -t wordpress-mcp:test .
WORDPRESS_TEST_IMAGE=wordpress-mcp:test uv run --frozen python -m unittest discover -s tests -v
```

Container tests use an isolated Docker network and a mock WordPress API. They
do not need real credentials or access to a WordPress site. PR CI runs them
on both amd64 and arm64.

The project structure:

```
wordpress-mcp/
├── src/
│   ├── config.py          # Configuration and WordPress client
│   ├── server.py          # FastMCP server setup
│   └── tools/             # Individual tool implementations
│       ├── posts.py       # Posts management
│       ├── users.py       # Users management
│       ├── media.py       # Media management
│       ├── categories.py  # Categories management
│       ├── tags.py        # Tags management
│       └── site.py        # Site settings
├── main.py                # Server entry point
└── pyproject.toml         # Dependencies and configuration
```
