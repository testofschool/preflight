import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
const SKILL_DIR='/Users/felix/.codex/plugins/cache/openai-primary-runtime/presentations/26.1015.12040/skills/presentations';
const root=process.cwd();
// G failed. Default to the preserved candidate, never to the selected v6 deliverable.
const candidate=path.resolve(root,process.argv[2] ?? 'reports/final_v7/candidate_v7/Preflight_v7_FAILED_G.pptx');
const digest=createHash('sha256').update(await fs.readFile(candidate)).digest('hex');
const {finalizePresentation}=await import(pathToFileURL(path.join(SKILL_DIR,'container_tools/artifact_tool_utils.mjs')).href);
await fs.mkdir(path.join(root,'reports/final_v7/track_g_build'),{recursive:true});
const staging=await fs.mkdtemp(path.join(root,'reports/final_v7/track_g_build/validated-'));
const result=await finalizePresentation({
 workspaceDir:root,
 candidatePath:candidate,
 finalPath:path.join(staging,'Preflight_pitch_deck.pptx'),
 pythonExecutable:'/Users/felix/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3',
 integrityValidatorPath:path.join(SKILL_DIR,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(SKILL_DIR,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','9144000,5143500','--validate-bullet-geometry','--validate-heading-fit'],
 explicitTotalSlideCount:12,
 requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],
 fontPolicy:{basis:'reference',families:['Google Sans Flex','Google Sans Flex Medium','Google Sans Flex SemiBold'],referencePath:path.join(root,'docs/template/aibc_template.pptx'),referenceSha256:'29923ab726aa1382946c70ff527c769f0b9e95a55e889f2e01e7ad62641ea629'},
 verifyArtifactToolImport:true,
 receiptPath:path.join(root,`reports/final_v7/track_g_finalizer_${digest.slice(0,12)}.json`)
});
console.log(JSON.stringify(result,null,2));
