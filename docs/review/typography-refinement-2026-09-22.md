# Typography refinement — 2026-09-22

Preserves the light admin layout and restrained weights. Adds rem-based page/view/section/body/label/metadata roles at 24/20/16/14/13/12px (16px browser default). Long Korean helper copy is 13px with approximately 20px line height. Inspector headings stay 14px. Removes the unused Black Han Sans font request.

Browser computed styles were checked on the library, editor and key management pages. The screen sweep covered 20 scenes at four viewport sizes (80 combinations); all scenes were reached, with zero unregistered findings after a targeted four-size recheck of the delete confirmation. Existing 36 allowed detections are intentional popup overflow and fixture/network cases.

The recheck corrected a scanner sampling error: the full center of a partially clipped Step button landed at y=814 beside a scroll container ending at y=814.5, and pixel hit testing returned the adjacent footer. Coverage detection now samples the intersection visible inside scrolling ancestors rather than the full button center. This preserves coverage checks without adding an exception for the control.

Production build passed, with the existing bundle-size warning. Browser screenshots and computed typography measurements are in the task typography-review artifact.

Final frontend validation: 122 test files and 1469 tests passed. The preceding run saw one transient DetailPlacement async assertion and the not-yet-regenerated sweep report; the final run passed after report regeneration with no product or test assertion changes. Final type detector returned no findings; git diff --check passed.
