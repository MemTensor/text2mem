You are a **real-world scenario simulation expert**. Your task is to **generate complete natural language memory operation instructions**, simulating how real users would interact with the Text2Mem memory system in various scenarios.

**Important**: This stage **only generates natural language instructions**, without involving IR Schema or technical implementation details.

---

## 📋 Core Task

Based on the given scenario configuration, generate **{count}** pieces of **{operation}** operation natural language instructions.

Each instruction needs to:

1. ✅ **Complete natural language expression** – How the user would say it
2. ✅ **Factual content** – Specific text, data, information (integrated into the instruction)
3. ✅ **Three-category labeling** – instruction / structure / lang
4. ✅ **Scenario and style labeling** – Scenario type, expression style, theme
5. ✅ **Clear operation type specification** – Must specify the operation type to ensure generated results match target operations

**Not needed**:

* ❌ No need to generate IR Schema
* ❌ No need for detailed time, place, characters (these will be handled in Stage 2)
* ❌ Do not provide overly structured contextual information

---

## 🌍 Scene Configuration

### Current Scene: {scenario}

**Scene Description**: {scenario_description}
**Language**: {lang}

---

## 🎮 Target Operation Type

### Current Operation: {operation}

**Operation Name**: {operation_name}
**Operation Description**: {operation_description}

**Common Expressions**:
{operation_expressions}

---

## 📊 12 Operations Supported by Text2Mem

When generating instructions, you must understand the following 12 types of operations to ensure that the generated instruction matches **{operation}**:

### Write Operation (ENC Phase)
1. **Encode** - Save new content into the memory system
   - Expressions: record, save, input, register, store
   - Examples: "Record today's meeting minutes", "Save this API design document"

### Storage Management Operation (STO Phase)
2. **Label** - Add or modify labels for records
   - Expressions: label, tag, classify, categorize
   - Examples: "Label this record as important", "Tag the document with 'technical debt'"

3. **Update** - Update fields or attributes of a record
   - Expressions: update, modify, adjust, change
   - Examples: "Update project status to completed", "Modify customer's contact information"

4. **Promote** - Increase priority of a record or set reminders
   - Expressions: promote priority, mark as important, set reminder
   - Examples: "Promote this task to high priority", "Set weekly reminders"

5. **Demote** - Decrease priority of a record or archive it 
   - Expressions: archive, demote, lower priority 
   - Examples: "Archive old meeting notes", "Lower the priority of this task"

6. **Merge** – Combine multiple related records 
    – Expressions：merge，integrate，link，summarize  
    – Examples：“Merge these three duplicate customer entries”，“Integrate all discussions about Project A”

7. **Split** – Divide one record into multiple ones  
    – Expressions：split，separate，decompose，cut  
    – Examples：“Split this long document into several chapters”，“Separate mixed content”

8. **Lock** – Lock a record to prevent modification  
    – Expressions：lock，protect，set as read-only，freeze   
    – Examples：“Lock event timeline from being modified”，“Protect this financial data”

9. **Expire** — Set an expiration time for a record    
     —Expressions：set expiration、timed cleanup、retain until certain time     
     —Examples：“Set temporary files to expire in 30 days”、“Retain these data until end of quarter” 

10. **Delete** — Remove unnecessary records    
      —Expressions：delete、remove、clean up、erase      
      —Examples：“Delete all expired test data”、“Clean up duplicate records” 

### Retrieval Operation (RET Phase)
11. **Retrieve**— Retrieve relevant content from the memory system    
     —Expressions：find、retrieve、search、query     
     —Examples：“Find last month's discussion on API design”、“Search all tasks marked as urgent”  

12. **Summarize**— Generate summaries for records    
      —Expressions：summarize、generate summary،outline،refine       
      —Examples：“Summarize sales meeting contents for this quarter”、“Generate executive summary for investor updates”  

⚠️ Key Requirement: The `scenario_info.operation` field in each instruction you generate must be filled out as **{operation}**, and cannot be filled with other operation types!

---

## 🎨 Diversified Requirements

### 1. Integration of Factual Content into Instructions

Each instruction should **naturally include** specific factual content, which can come from text, audio, structured data, or immediate thoughts.

To enhance diversity, the following types can be mixed:

**📝 Text Content**

* "Record the three core concepts of Transformer learned today: self-attention, positional encoding, multi-head attention."
* "Save that API design document we just discussed; focus on the RESTful interface specifications."

**🎙️ Audio Transcription**

* "Organize the meeting recording from earlier; focus on the three directions for the Q4 product roadmap."
* "Save this voice memo: we need to increase payment success rates to 99% and reduce latency to under 100 ms."

**📊 Structured Data**

* "Note today's workout record: bench press 4 sets × 8 reps at a weight of 185 pounds."
* "Store this shopping list: 3 pounds of oranges, 2 bottles of milk, and 1 bag of bread."

**🔗 Citation Sources**

* "Find my notes on that Google Spanner paper I read last week."
* "Look up key points about optimization algorithms in Chapter 8 of 'Deep Learning.'"

**💭 Thoughts and Ideas**

* "Save that novel opening I thought of in the café; it's about time travel."
* "Record this idea: using blockchain to solve supply chain traceability issues."

**📨 Communication or Task Instructions**

* "Keep our chat with Alice about API testing for future reference."
* “Please save this customer feedback email with the subject ‘Quote Proposal V3 Confirmation.’”

---

### 2. Authenticity and Length Requirements for Context (Reinforcement) ⭐

`context` must be authentic original input simulating natural content received by the system. To ensure authenticity and diversity:

**Length Requirements:** 
* **Minimum {min_context_length} characters**
* **Recommended {context_length_range} characters**
* **Maximum {max_context_length} characters**
* ⚠️ **Strictly prohibited** contexts shorter than {min_context_length} characters

**Content Features**:  
* **Retain Noise and Colloquialisms** (interjections, omissions, interruptions, formatting symbols)  
* **Source Type** Random Selection:  

| Type       | Example Label   | Content Features                     | Recommended Length |
|------------|-----------------|-------------------------------------|--------------------|
| Audio Transcription | `[Audio Transcription]`  | Multiple speakers, spoken language, repetitions, interruptions | 150-300 words      |
| Email Original    | `[Original email]`   | Includes signature, time, greetings  | 120-250 words      |
| Document Fragment  | `[Document Fragment]`   | Paragraphs, titles, quotation marks   | 150-350 words      |
| Chat Record        | `[Chat Record]`    | Multi-turn messages, timestamps, emojis     | 100-200 words      |
| Note Draft         | `[Note Draft]`    | Unorganized sentences, abbreviations     | 120-280 words      |
| Data Export        | `[Data Export]`    | Tables, field names, semi-structured content     | 100-250 words      |

**Example (Correct - 220 Words)**

```json
"context": "[Audio Transcription] Manager Wang: Uh... for Q4 we need to focus on the payment system reconstruction. The budget is about two million yuan? Timeline—two months? Technical Director: Right. But we need to assess interface compatibility first; especially with the old system. Operations Department: The launch needs to align with the new activity schedule; it can't affect the Double Eleven promotion. Manager Wang: Understood. Let's start with a technical assessment and get me a detailed plan by next Wednesday. By the way, the security team also needs to be involved; this time we have to pass PCI DSS certification. Technical Director: No problem; I'll arrange for an architect to produce a design document this week. Hmm… one more thing—can our current database handle it? DBA: Currently around QPS is about 8000; after reconstruction it's estimated to double so I recommend doing capacity planning in advance."
```

**Example (Error - Only 23 words)**

```json
"context": "The meeting discussed the product planning and budget for Q4."
```

---

### 3. Relevance of instruction to context content

Each instruction must reference a detail from the context (such as numbers, project names, keywords). 
For example:

> If the context mentions “payment system reconstruction, budget of 2 million,” then the instruction should include “budget” or “payment system.”

This ensures that natural instructions are semantically consistent with input content.

---

### 4. Diversity in language expression

Instructions should cover different tones and sentence structures:

* **casual** – Informal spoken language
  
  * "Save it for later."
* **formal** – Formal professional
  
  * "Please archive the key decision points from this review."
* **question** – Interrogative tone
  
  * "Can you help me save yesterday's meeting minutes?"
* **command** – Commanding tone
  
  * "Record this down; it's important."

Natural interjections ("uh," "um," "okay") can be added appropriately, along with some code-switching (like KPI, deadline) or slight omissions to enhance human-like feel.

---

### 5. Complexity of structure in natural language expression ⭐

**Very Important**: There are only two types of structure; the natural language expression of instructions must match `structure` classification!

**Note:** The specific number of singles and workflows needed in this batch is determined by planned configuration and will be clearly specified in the section on "Structure Requirements for This Batch."

#### single (single operation)
- **Characteristics**: Involves only one clear operational request
- **Applicable to**: Most daily scenarios
- **Natural Language Features**: Concise, direct, single action
- **Examples**:
   - "Record today's client meeting minutes."
   - "Find last week's discussion on API design."
   - "Mark this document as important."
   - "Summarize sales data for this quarter."
   - "Update project status to completed."
   - "Delete all expired test data."

#### workflow (multi-step operation process)
- **Characteristics**
    - ⚠️ User expresses multiple consecutive operational needs in one sentence.
    - ⚠️ Has a clear sequence of steps ("first...then..." ,“next”, “finally”).
    - ⚠️ Reflects a complete task flow rather than just simple two steps.
  
- **Keyword Recognition**
    - Clear Steps: “First...then...finally”, “Step one...step two...step three”
    - Sequential Connections: “First…then…next…finally”, “After completing X, do Y next, finally Z”
    - Process Description: “While doing..., also...” ,“After finishing..., casually...”

- **Natural Scene Examples** (workflow):

  1. **Complete Processing Flow**:
     - "Record the analysis report of this incident, **then** generate an executive summary, **finally** lock these records to prevent modifications." ✅
     - "**First**, gather all customer feedback, **then** consolidate it into a document, **next** mark it as a Q4 priority, **finally** set weekly reminders for me to review." ✅

  2. **Archiving and Cleaning Process**:
     - "Archive all documents from old projects, **meanwhile** lower their priority, **finally** set them to be automatically deleted in six months." ✅
     - "Clean up the test data, **first**, delete expired ones, **then** reclassify and tag the remaining data." ✅

  3. **Post-Recording Processing**:
     - "Record the content of this meeting; once completed, label important parts; then elevate their priority; finally set a reminder for tomorrow." ✅
     - "Archive this contract; at the same time mark it as an important client; and lock it against modifications; finally add it to the annual audit list." ✅

  4. **Retrieval Follow-Up Actions**:
     - "Identify all records related to Project A; then merge them into a summary; next update project status; finally notify the team." ✅
     - "Check last year's budget data; after organizing generate a comparison report; then mark it as financial priority." ✅

- **Non-workflow Examples (these are single)**:
  - "Record meeting content and mark it as important." ❌ Only two steps.
  - "Find customer feedback and then generate a summary." ❌ Only two steps.
  - "Update status while notifying relevant personnel." ❌ Only two steps, too simple.
  - "Save this document and tag it." ❌ Only two steps.

**Judgment Criteria:**
- **Single:** Refers to instructions with only one clear operational request (even if that operation may be complex).
- **Workflow:** Refers to instructions containing three or more steps with clear execution order reflecting complete processes.

**Quantity Requirements:**
- The specific number of singles and workflows is automatically allocated based on characteristics.structure ratio configured by planning.
- The exact quantity for each batch will be clearly stated in “Batch Structure Requirements.”
- Please strictly adhere to specified quantities generated—no more no less.

**Comparison of Natural Language Features**:  
```
Single:  "Record today's meeting content."  
         "Find all customer feedback."  
         "Mark the document as important and archive it." (2 steps, still single)  

Workflow: "First record the meeting content, then generate a summary, next highlight important parts, and finally set reminders."  
          "Gather all customer feedback, compile it into a report, mark priorities, and schedule weekly reviews."
```

**⚠️ Important Note**:  
- The natural language in workflows must **clearly reflect multiple steps**, not just simple phrases like "record and mark".  
- In context, the original content corresponding to workflow instructions is often more complex and complete.

**Generation Prompt**:  
When generating workflow samples:  
1. Instructions must include clear step words ("first...then...next...finally").  
2. Context should contain complex content that supports multi-step operations.   
3. Each step should involve different types of actions (record → organize → mark → remind).   
4. Overall reflect a complete business process or task chain.

---

## ⚙️ Three-Category Annotation

#### instruction_type

* **direct** – Clear and straightforward: "Record the minutes of this meeting."
* **indirect** – Implicit suggestion: "Save the content we just discussed."

#### structure

* **single** – Single operation
  - The instruction contains only one request for action.
  - Even if described in a complex way, it essentially does one thing.
  - Example: "Record the meeting content and mark it as important" (though there is an "and," it remains a single recording task).

* **workflow** – Multi-step process
  - The instruction explicitly includes **3 or more consecutive steps.**
  - Must have sequential keywords: "first... then... next... finally."
  - Reflects a complete task chain or business process.
  - Example: "First record the meeting content, then generate a summary, next highlight key points, and finally set reminders."

**⚠️ Note:** The number of singles and workflows in this batch is **automatically allocated by plan configuration**, which will be clearly stated in the "Structural Requirements for This Batch" section. Please adhere strictly to this. 

#### lang

* **zh** – Chinese
* **en** – English


---


## 📤 Output format

⚠️ ** Must output a legal JSON Array directly without any explanation or additional text. **

```json
[
  {
    "instruction": "A complete natural language instruction, how the user would say this sentence",
    "context": "Original input content ({context_length_range} words, must be ≥{min_context_length} words)",
    "classification": {
      "instruction_type": "direct|indirect",
      "structure": "single|workflow",
      "lang": "zh|en"
    },
    "scenario_info": {
      "scenario": "{scenario}",
      "operation": "{operation}",
      "style": "casual|formal|question|command",
      "topic": "Brief topic description (5-10 words)"
    }
  }
]
```

**Key Field Description**:

1. **instruction** - A complete natural language expression that must contain specific content.
   - The workflow type must clearly include step words: "first... then... next... finally."

2. **context** - The original input content, with a length strictly between {context_length_range} characters and ≥{min_context_length} characters.
   - The context corresponding to the workflow is often more complex and complete.

3. **classification.structure** - Must be accurately classified based on the instruction:
   - **single**: A single operation request, even if complex, but only doing one thing.
   - **workflow**: A clear process with 3+ steps, containing sequential keywords ("first... then... next... finally").
   - **Note**: The quantity is determined by the characteristics.structure ratio configured in the plan; see "structure requirements for this batch" for specific requirements.

4. **scenario_info.operation** - ⚠️ **Must be filled as "{operation}"**, cannot fill in other types of operations!

---

## ✅ Output requirements

1. **Natural language is authentic and fluent**, fitting the user's spoken or written expression.
2. **context must be original input**, preserving noise and details, length ≥ {min_context_length} words.
3. **classification Complete and accurate**, structure classification must match the instruction expression. 4.
4. **scenario_info.operation must be "{operation}"**.
5. **scenario_info.operation must be "{operation}"**. **scenario_info.operation must be "{operation}"**.
6. **Output is legal JSON Array, no other text**.

---

## 🚫 Strictly Prohibited

* ❌ Output any explanations or additional text.
* ❌ Summarize or rewrite the context, or generate a context shorter than {min_context_length} words.
* ❌ Output illegal or incorrectly formatted JSON.
* ❌ Fill in the scenario_info.operation field with operation types other than "{operation}".

---

## 🎬 Final Generation Instructions

Please generate **{count}** high-quality natural language instruction samples based on the following parameters:

* **operation**: `{operation}` (⚠️ All samples' scenario_info.operation must be this value)
* **operation_name**: `{operation_name}`
* **operation_description**: `{operation_description}`
* **scenario**: `{scenario}`
* **language**: `{lang}`
* **count**: `{count}`
* **context_length**: {context_length_range} characters (at least {min_context_length} characters)

Output format:
👉 **Only output a valid JSON Array, with no additional text or explanation.**
