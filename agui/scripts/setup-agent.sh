#!/bin/bash

# Navigate to the agent directory
cd "$(dirname "$0")/../../" || exit 1

uv sync
