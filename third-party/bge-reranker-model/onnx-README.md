---
library_name: transformers.js
base_model:
- BAAI/bge-reranker-v2-m3
---

# bge-reranker-v2-m3 (ONNX)

This is an ONNX version of [BAAI/bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3). It was automatically converted and uploaded using [this space](https://huggingface.co/spaces/onnx-community/convert-to-onnx).

## Usage (Transformers.js)

If you haven't already, you can install the [Transformers.js](https://huggingface.co/docs/transformers.js) JavaScript library from [NPM](https://www.npmjs.com/package/@huggingface/transformers) using:
```bash
npm i @huggingface/transformers
```

**Example:** Reranking text using the BGE Reranker model.

```js
import { pipeline } from '@huggingface/transformers';

const reranker = await pipeline('text-classification', 'onnx-community/bge-reranker-v2-m3-ONNX');
const output = await reranker('I love transformers!');
```