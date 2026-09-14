# V28.0 Registered Agent Tools

The model may request only the following stable tools. Every call is schema-validated, permission-checked, revision-bound, and audited without secrets.

## Read and selection

- `read.project_summary`
- `read.page_summary`
- `read.selection_summary`
- `selection.select_layers`

## Objects and rich text

- `object.create_text`
- `object.create_image`
- `object.create_shape`
- `object.update`
- `object.duplicate`
- `object.delete`
- `rich_text.replace`

## Transform and grouping

- `transform.move`
- `transform.resize`
- `transform.rotate`
- `transform.align`
- `transform.distribute`
- `transform.tidy`
- `transform.group`
- `transform.ungroup`
- `transform.arrange`

## Style and media

- `style.apply_text_style`
- `style.apply_palette`
- `style.apply_brand_kit`
- `style.apply_photo`
- `photo.remove_background`

## Pages and invitation fields

- `page.create`
- `page.duplicate`
- `page.rename`
- `page.reorder`
- `event.update_fields`
- `event.update_schedule`

## Assets and checks

- `asset.search`
- `asset.insert`
- `check.design`
- `check.accessibility`
- `check.layout`
- `check.print`
- `fix.apply`

## Preview and external boundaries

- `preview.prepare`
- `export.prepare`
- `publish.prepare`
- `message.prepare_send`

`publish.prepare` never bypasses the product's existing publish confirmation and server policy. `message.prepare_send` stores a prepared draft boundary and never dispatches a campaign. `photo.remove_background` calls the existing confirmed local workflow and may create an authorized material derivative.
