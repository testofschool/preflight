Challenge = Media, Content & Digital Experiences

Prototype link = https://preflight-jcgro45veq-as.a.run.app

GitHub link = https://github.com/testofschool/preflight

Demo video = <VIDEO_URL>

Brief description = Preflight checks an AI-video prompt before you pay to generate it. Paste a text-to-video prompt and get a failure-risk estimate learned from 1,911 human pairwise votes (GenAI-Bench), the nearest historical prompts as evidence, and a Gemini rewrite kept only when the estimated risk drops. Two more rungs close the loop: a still-image preview (built, disabled in this build) and an upload-based clip review with Gemini video understanding as a second pair of eyes. Google Cloud: the FastAPI app runs on Cloud Run (asia-southeast1, min-instances 0). Votes, IRT difficulty parameters, feedback and cached previews live in Cloud Firestore, the Firebase document database. Gemini 3.5 Flash on Vertex AI powers the rewrite agent, built with Google ADK and persisted via Agent Platform Sessions; Gemini image and video models provide the preview and clip review. Limits are stated in-product: the risk score is a historical signal (held-out AUC 0.67), not a calibrated probability; clip-review accuracy is unmeasured.
