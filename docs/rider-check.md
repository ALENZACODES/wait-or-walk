# Rider check: a 10 minute script for five riders (not yet run)

No rider testing has been done. This is a script John can run, if he chooses, with five people who ride the TTC subway. Each session takes about 10 minutes, on the rider's own phone or one handed to them. Nothing below is a result; the table at the end is empty until a real session fills it.

## Ground rules
- Ask first: "I am testing a page I built for subway delays. It takes 10 minutes. I will take notes, no names and no recordings. Is that OK?" Stop if they say no.
- Record only: how often they ride (daily, weekly, rarely), their usual line, and the notes below. No names, no photos.
- Do not explain the page before or during the tasks. If they are stuck for 60 seconds, note "stuck" and move to the next task.
- Use the same page for all five: the live page at https://alenzacodes.github.io/wait-or-walk/ (the code is frozen at the tag slay-hacks-submission). Do not change the page between riders.
- Say once at the start: "Please think aloud. There are no wrong answers; if something is confusing, that is the page's fault."

## Five tasks (about 2 minutes each)
1. **The Kipling warning.** Tap "Person at track level, Kipling". Ask: "What is the page telling you to do, and why?"
   Note: did they say wait (yes / no / unsure), and did they mention the delay estimate against the bus time?
2. **The 23%.** Point at the 23%. Ask: "What does this number mean?"
   Note: correct if they say something like "the chance a delay like this lasts 10 minutes or more". Note it if they read it as their own wait, as the chance the alert is true, or anything else. Then ask: "Does it matter that it only counts incidents that actually delayed service?" Note the answer as said.
3. **Already underway.** Ask: "Say you have already waited 5 minutes. Show me how you would tell the page that."
   Note: did they find and tap "Delay already reached 5 min" (yes / no / with a hint), and did they notice the number change?
4. **The next Plan B departure.** Ask: "If you left now, which bus would you take, and when does it leave?"
   Note: did they find the first scheduled departure under Plan B (yes / no), and did they mention that times are timetable estimates?
5. **Why St George switches.** Tap "Fire at St George, headed to Dupont". Ask: "Why does the page say to switch here but not at Kipling? What would make switching a bad idea?"
   Note: did they mention the longer expected delay, and did they mention a late or missed bus (the timetable risk lines)?

Close with one question: "What is the one thing you would change?" Write the answer as said.

## Results table (empty until real sessions are run)

| Rider | Rides | Task 1: said wait | Task 2: read 23% correctly | Task 3: found the button | Task 4: found the next departure | Task 5: named a late or missed bus | One change, as said |
|---|---|---|---|---|---|---|---|
| 1 | | | | | | | |
| 2 | | | | | | | |
| 3 | | | | | | | |
| 4 | | | | | | | |
| 5 | | | | | | | |

## Reporting
- Report counts out of 5 for each task, plus the quotes as said, including the bad ones. Five riders find the biggest problems; they do not measure how well the page works for everyone, so do not turn the counts into percentages for all riders.
- Fix at most the two biggest problems found, then say what was changed and why. Any change to `logic.js`, the model or the verdict rule is a change after the freeze and must be listed in `docs/freeze.md`.
- Date the sessions and say where they were run (for example, on a platform or at home). If fewer than five were run, say how many.

The older, longer script with five questions is in `docs/rider-test.md`.
