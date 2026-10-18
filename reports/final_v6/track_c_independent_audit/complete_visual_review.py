from pathlib import Path
import json, hashlib
R = Path('reports/final_v6/track_c_independent_audit')
p = R/'audit.json'
d = json.loads(p.read_text())
capture = json.loads(Path('reports/final_v6/track_c_supplement_capture.json').read_text())
fixture = json.loads(Path('cloud/sample_rewrites.json').read_text())
allowed = set(capture['status_before']['sample_prompts']) | {r['rewrite']['rewritten_prompt'] for r in fixture['samples']}
response = capture['preflight_response']
basehash = hashlib.sha256(Path('scripts/record_demo.py').read_bytes()).hexdigest()
source = {
 'own_original_outside_complete_original_and_rewrite_sample_whitelist': capture['prompt'] not in allowed,
 'own_rewrite_outside_complete_original_and_rewrite_sample_whitelist': response['rewritten_prompt'] not in allowed,
 'preview_UI_payload_selection': 'static/app.js241-243 selects the accepted rewrite for Preview a still; this exact non-sample rewrite is shown in captured UI. Network receipt does not log request bodies.',
 'frozen_base_capture_script_unchanged': capture['capture_base_script_sha256'] == capture['capture_base_script_sha256_after'] == basehash,
 'recorded_typed_prompt': capture['prompt'],
 'recorded_rewrite_source': response['rewrite_source'],
 'recorded_rewrite_status': response['rewrite_status'],
 'request_specific_observed_risk_percent': {'before': round(response['p_fail_before']*100,1), 'after': round(response['p_fail_after']*100,1)},
 'image_count_provenance_boundary': 'No visible cumulative counter; hardcoded API generations=0 is not evidence of usage. The recorded HTTP503 non-sample request path, source guard, and sample-mode flags support zero image-model calls for this new preview interaction.'
}
(R/'supplement_source_crosscheck.json').write_text(json.dumps(source,indent=2)+'\n')
observations = [
 {'seconds':5, 'observed':'Quote intro and large burned caption readable; unchanged original beat.'},
 {'seconds':70, 'observed':'Saved rewrite still and zero-model-call/zero-cost label visible; original caption readable.'},
 {'seconds':95, 'observed':'Live typed-prompt rewrite visible, 13.3% original to 3.3% rewrite line. These figures belong to the distinct own prompt, not the spoon sample.'},
 {'seconds':100, 'observed':'Within new segment; UI is moving toward preview action, own-prompt caption readable. Limited message is not yet shown at this exact frame.'},
 {'seconds':102, 'observed':'Real red limited-preview message and matching large caption both visible, no generated image.'},
 {'seconds':110, 'observed':'What this score is expanded; 1,911/0.67 historical-signal explanation and preview-limited message visible, large caption readable.'},
 {'seconds':140, 'observed':'Existing clip-review result, machine-feedback separation and source synthetic-clip label visible; original caption readable.'},
 {'seconds':180, 'observed':'Limits card, AUC 0.67, best 8/20, zero sample calls/cost, clip-review accuracy unmeasured visible; original caption readable.'}
]
d['visual_review'] = 'PASS: all 8 independently decoded requested/action frames plus all 3 new-caption midpoint frames visually inspected. No unreadable new caption, fabricated number claim, text overflow, or introduced UI replacement observed. The 1:40 frame is new-segment action; the 1:42 frame explicitly shows the limitation. The 2:20 frame remains clip review as approved.'
d['visual_review_PASS'] = True
d['visual_observations'] = observations
d['supplement_source_crosscheck'] = source
d['PASS'] = d['automated_PASS'] and d['visual_review_PASS'] and all(source[k] for k in ['own_original_outside_complete_original_and_rewrite_sample_whitelist','own_rewrite_outside_complete_original_and_rewrite_sample_whitelist','frozen_base_capture_script_unchanged'])
p.write_text(json.dumps(d,indent=2)+'\n')
cap = json.loads((R/'caption_burned_checks.json').read_text())
beats = json.loads((R/'preserved_beat_comparisons.json').read_text())
print({'PASS':d['PASS'], 'caption_count':cap['all_active_cues_checked'], 'minimum_bright_glyph_fraction':min(x['bright_glyph_fraction'] for x in cap['rows']), 'maximum_preserved_beat_MAE':max(x['mean_abs_channel_difference'] for x in beats), 'source_crosscheck':source})
