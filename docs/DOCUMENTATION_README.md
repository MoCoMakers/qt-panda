# Documentation Guide

## File Naming Conventions

### Master Documentation Files
**All published documentation master copies must be named in ALL CAPS.**

- Example: `PREAMP.md`, `Z_CONTROLLER.md`, `ELECTRONICS.md`
- These master files are located in the `documentation/` root directory
- They serve as the primary, published versions of documentation

### Reference Files
- Raw notes and reference materials are stored in `documentation/references/`
- These may use mixed case naming (e.g., `preamp.md`, `image_map.csv`)
- Reference files are working documents and may be less polished

## Image Labeling System

### Overview
Images are managed through a centralized mapping system using `references/image_map.csv`. This ensures consistent labeling, proper alt text, and easy reference across documentation.

### Image Label Format
When referencing images in source documents, use the format:
```
Image Label: LABEL_NAME
```

Where `LABEL_NAME` matches an entry in `references/image_map.csv`.

### Image Map CSV Structure
The `image_map.csv` file contains the following columns:
- **Label**: Unique identifier for the image (e.g., `PREAMP_ORIG_1`)
- **Filename**: Actual image filename (e.g., `PREAMP_ORIG_1.png`)
- **Source Document**: Source document name (e.g., `PreAmp`)
- **Alt Text**: Descriptive text for accessibility and image context

### Example Image Map Entry
```csv
Label, Filename, Source Document, Alt Text
PREAMP_ORIG_1, PREAMP_ORIG_1.png, PreAmp, This shows the preamp used by MechPanda
```

### Using Images in Published Documentation

When creating or updating published documentation (master files in ALL CAPS):

1. **Locate image references** in source documents marked with `Image Label: LABEL_NAME`
2. **Look up the image** in `references/image_map.csv` to get:
   - The filename
   - The alt text
3. **Insert the image** using markdown syntax:
   ```markdown
   ![Alt Text](images/FILENAME.png)
   ```
4. **Place images** in the `documentation/images/` directory

### Image Label Naming Conventions
- Use UPPERCASE with underscores (e.g., `PREAMP_ORIG_1`)
- Be descriptive but concise
- Include version or variant indicators when applicable (e.g., `_ORIG_`, `_V2_`, `_DETAIL_`)
- Group related images with a common prefix (e.g., `PREAMP_*`, `Z_CONTROLLER_*`)

## Creating Published Documentation

### Workflow
1. **Source Material**: Start with reference files in `documentation/references/`
2. **Identify Images**: Find all `Image Label: LABEL_NAME` references
3. **Map Images**: Cross-reference with `references/image_map.csv`
4. **Create Master File**: Generate a well-structured markdown file in the documentation root
5. **Naming**: Use ALL CAPS for the master file name (e.g., `PREAMP.md`)
6. **Embed Images**: Include images using markdown image syntax with proper alt text
7. **Organize Content**: Structure the document with clear sections, headers, and formatting

### Documentation Structure
Published documentation should include:
- Clear title and overview
- Well-organized sections with headers
- Embedded images where referenced
- Proper markdown formatting
- Links to external resources
- Component specifications when applicable

### Example: Converting Reference to Published Doc

**Reference File** (`references/preamp.md`):
```markdown
Image Label: PREAMP_ORIG_1
Notice that the 100M ohm Ohmite resistor is hanging above the board...
```

**Published File** (`PREAMP.md`):
```markdown
### Resistor Placement
![This shows the preamp used by MechPanda](images/PREAMP_ORIG_1.png)

The 100M ohm Ohmite resistor is suspended above the board...
```

## Image Storage

- All images are stored in `documentation/images/`
- Image filenames should match the `Filename` column in `image_map.csv`
- Use descriptive filenames that match their labels (e.g., `PREAMP_ORIG_1.png`)

## Best Practices

1. **Always use the image map** - Don't hardcode image paths or alt text
2. **Keep alt text descriptive** - Update `image_map.csv` with meaningful descriptions
3. **Maintain consistency** - Use the same labeling conventions across all documents
4. **Update the map** - When adding new images, add entries to `image_map.csv`
5. **Master files are authoritative** - Published docs (ALL CAPS) are the source of truth
6. **Reference files are working docs** - Keep raw notes in `references/` for context

## Notes

- Master documentation files serve as the published, polished versions
- Reference files may contain meeting notes, raw data, or working drafts
- The image mapping system ensures images can be easily referenced and updated
- All published documentation should be self-contained and readable without referencing source files

