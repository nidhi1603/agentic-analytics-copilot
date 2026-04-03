# Chunking Strategy

The retrieval layer uses simple paragraph-based chunking with a target chunk size of about 800 characters and a small overlap between chunks.

## Why Chunking Exists

Large documents are broken into smaller pieces because embedding and retrieval work better when each indexed unit covers one focused idea instead of an entire file.

## Current Defaults

- max chunk size: 800 characters
- overlap: 120 characters

## Why This Is Good Enough For V1

- easy to understand
- easy to debug
- works well for short operational documents

Later versions could move to heading-aware chunking, token-based chunking, or reranking for better retrieval quality.

