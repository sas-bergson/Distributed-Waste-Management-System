# Code of Conduct

## Our Pledge

We are a cohort of students building the **Distributed Waste Management System (DWMS)** as a capstone project in Distributed Systems and Cloud Computing. We pledge to make participation in this project a harassment‑free, genuinely educational experience for everyone — regardless of experience level, language, disability, neurotype, appearance, gender identity or expression, sexual orientation, religion, nationality, academic background, or the grade you are currently on track to receive.

We recognise that a capstone is a **learning environment before it is a product**. People will be wrong in public, will break `main`, will misunderstand the assignment, and will ask questions that seem obvious. That is the point of the exercise. Our standard is not "never make mistakes" — it is "make the mistake visible and help fix it."

---

## Scope

This Code applies to everyone participating in this project: students, maintainers, instructors, teaching assistants, and external contributors.

It applies in **all project spaces**, including but not limited to:

- the GitHub repository (issues, pull requests, code review comments, commit messages, Discussions, wiki)
- project chat channels (WhatsApp, Discord, Slack, Teams) and email threads
- stand‑ups, lab sessions, pair‑programming sessions, and design meetings
- presentations, demos, poster sessions, and capstone defence
- any public space where you are representing the project or the course

It also applies when a project participant's conduct outside these spaces creates a hostile environment for other participants inside them.

---

## Expected Behaviour

### 1. Respect the learner, critique the work

Technical disagreement is expected and welcome — design arguments are how the architecture gets good. Direct your criticism at the **design, the code, the evidence**, never at the person. Compare these:

- ✅ *"This viewport query will do a full table scan once we pass ~50k locations — can we add a GiST index and show the query plan?"*
- ❌ *"You clearly don't understand spatial indexes. Did you even read the PostGIS docs?"*

The first is a review comment. The second is a person being made to feel stupid in front of their team. The second is not tolerated here.

### 2. Assume competence, ask before explaining

Assume your teammate has a reason for the code you are reading; ask what it was before rewriting it. A PR that "fixes" someone's work without a word in the issue thread is a small act of disrespect, and it is one of the most common ways capstone teams quietly fall apart.

### 3. Make room for different levels of experience

Some students are strong in Python, others in frontend, others in documentation, others in testing and QA. **None of these is worth more than another to this project**, and none is a licence to condescend to the people whose strength is elsewhere. If you are the person who understands PostGIS, your job includes explaining it — not gatekeeping it.

### 4. Communicate in the open

Prefer issues, PR comments, and Discussions over private DMs for technical decisions. Private decisions exclude teammates, produce duplicated work, and cannot be graded fairly. It is fine to DM someone for a personal matter or to ask for help privately — just do not use private channels for project decisions.

### 5. Share the credit honestly

This project is graded, and credit matters. In every PR description, state who did what if multiple people contributed. In presentations and reports, **name the people who built the thing**. Do not present a teammate's work as your own, and do not quietly omit a contributor.

### 6. Keep the repository safe

- No secrets, credentials, API keys, or `.env` files in commits.
- No real citizen data — no names, phone numbers, precise home coordinates, or device identifiers belonging to actual people. Use the simulators.
- If you discover a leaked secret or a privacy problem, report it privately to a maintainer **immediately** rather than in a public issue.

### 7. Behave professionally under deadline

The last two weeks of a capstone are stressful. Stress is an explanation for sharpness, not a justification for it. If you snap at someone, apologise and move on — the project has a short timeline, and resentment festers fast when nobody names it.

---

## Unacceptable Behaviour

The following are **not** tolerated in this project:

- **Harassment**, including offensive comments about a person's identity, experience level, academic ability, or grade; deliberate intimidation; following; inappropriate physical contact; unwelcome sexual attention; and sustained disruption of discussion.
- **Personal attacks** of any kind. Critique the work.
- **Dismissing or belittling** a teammate for asking a question, for not knowing a technology, or for making a mistake.
- **Exclusionary behaviour:** scheduling decisions in private channels to keep someone out, ignoring a teammate's PRs without explanation, or silently removing someone from work they contributed to.
- **Plagiarism and dishonest credit:** submitting another person's or team's code as your own, copying work from a previous cohort or from a public repository without attribution, ghostwriting (having someone else do your portion), or taking sole credit for shared work. See [Academic Integrity](#academic-integrity) below.
- **Doxxing:** publishing someone's private contact details, precise location, or personal information without consent.
- **Privacy violations:** storing, committing, or sharing real data about identifiable people, including real citizens' waste reports and locations.
- **Sabotage:** deliberately breaking `main`, deleting others' branches, corrupting seed data, or reverting a teammate's merged work without discussion.
- **Retaliation** against anyone who reports a concern or participates in an investigation.

---

## Academic Integrity

This repository is a **graded deliverable**. The open‑source licence (MIT) governs the *code*; it does not override your institution's rules, which govern *you*.

- **Your institution's academic integrity policy takes precedence** over anything in this document. Read it.
- **Team code is shared; individual credit is not.** You may build on any teammate's merged work — that is the whole point of a shared repository. You may not claim authorship of it in your individual report.
- **External code must be attributed.** If you adapt a snippet, library, tutorial, or answer from Stack Overflow or an LLM, cite it in the PR description. Untraced copying is plagiarism, even when the code is technically correct.
- **Cross‑team copying is prohibited.** Reading another team's public repository for inspiration is normal; copying their implementation is academic misconduct. If in doubt, ask the instructor before you copy a single function.
- **Do not share your cohort's unpublished work with other teams** without permission.

### AI‑assisted contributions

AI tools may be used as a **learning aid** — to explain a PostGIS function, to draft a test, or to review your own code — subject to your institution's policy, which you must follow.

The rule in this repository is **disclosure**:

- If an AI tool generated or substantially shaped a contribution, say so in the PR description under *AI assistance* (which tool, what it produced, and **how you verified it**).
- **You are responsible for every line you submit.** "The model wrote it" is not a defence in review or in assessment. Unverified generated code that breaks `main` is your failure, not the tool's.
- **Do not paste secrets, credentials, or personal data into any AI tool.**
- Undisclosed AI‑generated work presented as your own understanding may be treated as an academic integrity matter by your instructor, independent of this document.

Disclosure is not a penalty. Honest disclosure is exactly the behaviour this Code exists to encourage; concealment is the problem.

---

## Reporting

If you experience or witness unacceptable behaviour, you have options, and you may use **any** of them:

1. **Speak to the person directly**, if you feel safe doing so and it is a minor matter. A private "that comment landed badly" resolves a surprising amount.
2. **Contact a maintainer** — the student maintainers are listed in the [README](README.md). You can message any of them privately on GitHub or in the course chat.
3. **Contact the course instructor or TA directly.** You do not need permission from the maintainers, and you do not need to have tried the other steps first.
4. **For anything involving academic integrity, grades, harassment by a maintainer, or something you believe is serious — go straight to the instructor.** Student maintainers are your peers; they are not equipped or authorised to adjudicate those matters.

**What to include:** what happened, when and where, who was involved, and any links or screenshots. You do not need to write a formal report, and you do not need to be certain about whether it "counts."

### What happens to your report

- **Confidentiality:** reports are shared only with the people needed to respond — the maintainers and/or the instructor. Your identity is not disclosed to the person complained about without your agreement, except where the institution's process requires it.
- **No retaliation.** Retaliating against a reporter or witness is itself a Code violation and will be handled as seriously as the original behaviour.
- **Timeline:** maintainers will acknowledge a report within **72 hours**. If it involves the instructor's authority, they will acknowledge within their own office hours response time.
- **We will not pressure you to resolve it informally** if you have asked for it to be handled formally.

---

## Enforcement

Maintainers and the instructor will follow these guidelines in determining consequences. Responses escalate with the severity and repetition of the behaviour.

### 1. Correction (private)

**For:** a first, minor, unwitting infraction — a dismissive comment, a hardcoded colour, an undisclosed generated snippet, a PR merged without review.

**Response:** a private message from a maintainer explaining what was wrong and why, and what is expected going forward. No public record. Most issues end here, which is the desired outcome.

### 2. Warning (documented)

**For:** a repeated infraction, or a single comment that clearly demeaned a teammate.

**Response:** a written warning naming the behaviour and its impact, with a stated expectation and a timeframe for change. A note is kept so that a pattern can be recognised. Continued behaviour leads to step 3.

### 3. Temporary restriction

**For:** a serious violation, or continued behaviour after a warning.

**Response:** temporary removal of write access to the repository and/or a requirement that contributions go through maintainer review; a mandatory break from a specific project channel or collaboration pairing; a documented conversation with the instructor. Duration is stated in writing.

### 4. Permanent removal and academic referral

**For:** harassment, doxxing, sabotage, a privacy violation involving real data, plagiarism, or any behaviour that persists after step 3.

**Response:** permanent removal from the repository and project, a formal report to the course instructor, and where the institution's policy requires it, referral to the academic integrity or student conduct process.

> **Boundary of maintainer authority.** Student maintainers can apply steps 1–3. They **cannot** award, deduct, or negotiate grades, and they cannot overrule the instructor. Any matter that may affect assessment is referred to the instructor, who decides independently of this Code.

---

## Attribution

This Code of Conduct is adapted from the [Contributor Covenant](https://www.contributor-covenant.org/), version 2.1, with substantial additions for **academic integrity, contribution credit, AI disclosure, and data privacy** appropriate to a graded student capstone project.

Community Impact Guidelines were inspired by [Mozilla's code of conduct enforcement ladder](https://github.com/mozilla/inclusion).

---

## Questions

If you are unsure whether something you are about to do is acceptable — a comment, a design decision, an AI‑assisted contribution, a piece of data — **ask a maintainer before you do it**. Nobody has ever been penalised for asking this question first.

---

*Last reviewed: [date] — by [maintainers + instructor]*
