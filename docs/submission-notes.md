Challenge = Media, Content & Digital Experiences

Prototype link = https://preflight-jcgro45veq-as.a.run.app

GitHub link = https://github.com/testofschool/preflight

Demo video = <VIDEO_URL>

Brief description = Preflight checks an AI-video prompt before you pay to generate it. Paste a prompt for a failure-risk estimate from 1,911 human pairwise votes (GenAI-Bench), nearby evidence and a Gemini rewrite kept only when estimated risk drops. Five sample prompts have saved rewrite decisions and saved stills; when no lower-risk rewrite passes, the original stays. Stills show their generation date, zero model calls and $0.00. Live still generation is limited. Upload-based Gemini clip review provides a second pair of eyes. The FastAPI app runs on Cloud Run (asia-southeast1, min-instances 0). Historical votes, IRT parameters, separate machine feedback and saved stills live in Cloud Firestore. Gemini 3.5 Flash on Vertex AI powers the Google ADK rewrite agent, with Agent Platform Sessions. The risk score is a historical signal (held-out AUC 0.67), not a calibrated current-model probability; clip-review accuracy is unmeasured. No video generation is called.

Preview status = Image preview — Active for sample prompts (saved stills); live generation limited

Preview evidence = All three live-image probes failed the 19/20 reliability gate: P1 8/20, P2 6/20 and P3 6/20. Four saved sample decisions contain lower-risk rewrites; indoor gymnasium remains unchanged. Release evidence: ../reports/preview_v4/REPORT.md
