# Skills Guide

Skills are LLM-readable instruction files that teach the agent domain-specific workflows. They follow the [Agent Skills](https://agentskills.io) specification.

## How Skills Work

Unlike tools (which execute code), skills provide instructions that guide the agent's behavior. The flow:

1. **Discovery** -- omagent scans for `SKILL.md` files at startup
2. **Summary** -- available skills are listed in the system prompt as XML:
   ```xml
   <available_skills>
     <skill name="eda">Exploratory data analysis workflow</skill>
     <skill name="cleaning">Data quality and imputation</skill>
   </available_skills>
   ```
3. **On-demand loading** -- when the LLM needs a skill, it calls the `Skill` tool:
   ```json
   { "skill": "eda" }
   ```
4. **Instructions delivered** -- the full SKILL.md content is returned as a tool result, entering the conversation history (not the system prompt)

This "Skill-as-Tool" pattern keeps the system prompt small while making skill instructions available when needed.

## Skill Discovery Paths

omagent discovers skills from multiple locations:

1. **Pack directory** -- `{pack_dir}/skills/{skill_name}/SKILL.md`
2. **Project-local** -- `.omagent/skills/{skill_name}/SKILL.md` (in current directory)
3. **User global** -- `~/.omagent/skills/{skill_name}/SKILL.md`
4. **Claude skills** -- `~/.claude/skills/{skill_name}/SKILL.md`
5. **Walk-up** -- searches parent directories for `.omagent/skills/` or `.claude/skills/`

Priority: first found wins. Pack skills take precedence over user skills.

## Creating a Skill

### Step 1: Create the Directory

```bash
mkdir -p my-skill
```

### Step 2: Write SKILL.md

Every skill needs a `SKILL.md` file with YAML frontmatter:

```markdown
---
name: my-skill
description: One-line description of what this skill teaches
allowed-tools: tool1 tool2 tool3
metadata:
  pack: my_pack
  version: "1.0"
  user-invocable: "true"
---

## My Skill Workflow

### Step 1: Understand the Input
- Check what data is available
- Validate the format

### Step 2: Process
- Apply the technique
- Handle edge cases

### Step 3: Present Results
- Create visualizations
- Write a summary
- Save artifacts to the workspace
```

### Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Unique skill identifier (kebab-case) |
| `description` | Yes | One-line description shown to the LLM |
| `allowed-tools` | No | Space-separated list of tools this skill uses |
| `metadata` | No | Key-value pairs for additional info |

### Metadata Fields

Custom fields go inside `metadata`:

| Field | Description |
|-------|-------------|
| `pack` | Which pack this skill belongs to |
| `version` | Skill version |
| `user-invocable` | `"true"` or `"false"` -- can users invoke via slash command |
| `level` | Complexity level (informational) |
| `triggers` | Keywords that suggest this skill (informational) |

### Body Content

The Markdown body after frontmatter is the skill's instructions. Write it for the LLM:

- Use clear, actionable steps
- Reference specific tools by name
- Include examples where helpful
- Be concise -- this goes into the context window

## Skill with Scripts

Skills can include executable scripts:

```
my-skill/
  SKILL.md
  scripts/
    analyze.py
    generate.py
```

Reference them in the SKILL.md:

```markdown
## Step 3: Generate Report

Run the report generator:
```python
python scripts/generate.py --input data.csv --output report.html
```
```

## Skill with References

Skills can include reference documents:

```
chart-visualization/
  SKILL.md
  references/
    generate_bar_chart.md
    generate_line_chart.md
    generate_scatter_chart.md
```

The SKILL.md can reference these for detailed instructions on specific chart types.

## Examples

### Data Analysis Skill

```markdown
---
name: data-analysis
description: Analyze CSV and Excel files using DuckDB SQL queries
allowed-tools: sql_query read_file write_file
metadata:
  pack: data_science
  user-invocable: "true"
---

## Data Analysis with DuckDB

### Loading Data

```sql
-- CSV files
SELECT * FROM read_csv_auto('path/to/data.csv') LIMIT 5;

-- Excel files
SELECT * FROM read_xlsx('path/to/data.xlsx', sheet='Sheet1');
```

### Common Queries

**Summary statistics:**
```sql
SELECT
  COUNT(*) as total_rows,
  COUNT(DISTINCT category) as unique_categories,
  AVG(amount) as avg_amount
FROM read_csv_auto('data.csv');
```

**Group by analysis:**
```sql
SELECT category, COUNT(*), AVG(value)
FROM read_csv_auto('data.csv')
GROUP BY category
ORDER BY COUNT(*) DESC;
```
```

### Flutter Skill

```markdown
---
name: firebase-setup
description: Firebase integration and FlutterFire configuration
allowed-tools: flutter_cli read_file write_file pubspec_manager
metadata:
  pack: flutter_dev
  user-invocable: "true"
---

## Firebase Setup for Flutter

### Prerequisites
- Firebase CLI installed: `npm install -g firebase-tools`
- FlutterFire CLI: `dart pub global activate flutterfire_cli`

### Steps

1. **Create Firebase project** (if needed):
   ```bash
   firebase login
   firebase projects:create my-app
   ```

2. **Configure FlutterFire:**
   ```bash
   flutterfire configure --project=my-app
   ```

3. **Add dependencies:**
   ```yaml
   # pubspec.yaml
   dependencies:
     firebase_core: ^3.0.0
     firebase_auth: ^5.0.0  # if using auth
   ```

4. **Initialize in main.dart:**
   ```dart
   void main() async {
     WidgetsFlutterBinding.ensureInitialized();
     await Firebase.initializeApp(
       options: DefaultFirebaseOptions.currentPlatform,
     );
     runApp(MyApp());
   }
   ```
```

## Using Skills

### As a User

Invoke skills directly with slash commands:

```
> /eda
> /firebase-setup
> /data-analysis
```

Or just describe what you need -- the agent will find the right skill:

```
> I need to clean this dataset, it has lots of missing values
```

### Programmatically

```python
from omagent.core.skill_loader import SkillRegistry

registry = SkillRegistry()

# Discover skills
count = registry.discover([Path("./skills")])

# Look up a skill
skill = registry.get_by_name("eda")  # case-insensitive
content = registry.get_full_content("eda")

# List all skills
for skill_info in registry.list_all():
    print(f"{skill_info['name']}: {skill_info['description']}")

# Get XML for system prompt
xml = registry.get_prompt_xml()

# Get user-invocable skills (for slash commands)
invocable = registry.get_user_invocable()
```

## Validation

omagent uses the [skills-ref](https://github.com/anthropics/skills-ref) library to validate skills on load. Skills that fail validation are skipped with a warning.

Common validation errors:

| Error | Fix |
|-------|-----|
| Missing `name` field | Add `name:` to frontmatter |
| Missing `description` field | Add `description:` to frontmatter |
| Unknown top-level field | Move custom fields into `metadata:` |
| No frontmatter | Add `---` delimiters with YAML |

You can validate skills manually:

```bash
# If skills-ref CLI is installed
skills-ref validate path/to/skill/
```
