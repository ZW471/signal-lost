# Signal Lost (信号遗失) — NPC Definitions

This file defines all major and minor NPCs. The agent must maintain each NPC's personality, speech patterns, knowledge boundaries, and disposition consistently across all interactions. NPCs are the primary gatekeepers of truth — they reveal information only when trust conditions are met and evidence is presented.

**Core principle:** Every NPC knows more than they say. What they share depends on trust level, what the player has proven they already know, and whether sharing serves the NPC's own goals.

---

## Disposition System

Each major NPC has a **disposition** toward the player: `hostile`, `wary`, `neutral`, `friendly`, or `allied`.

### Trust Level Behaviors

| Level | Interaction | Information | Risk |
|-------|------------|-------------|------|
| **Hostile** | Refuses interaction; may attack, betray, or report player to NEXUS | None | NPC actively works against player |
| **Wary** | Minimal conversation; guarded body language; may demand payment for basics | Surface-level only — rumors, public knowledge | NPC will not warn player of danger |
| **Neutral** | Standard interaction; willing to trade, answer direct questions | Layer 1 knowledge; general facts about their area | NPC is indifferent to player's fate |
| **Friendly** | Shares deeper knowledge; offers help; initiates conversation | Layer 2-3 knowledge (depending on NPC); personal stories | NPC will warn player of known threats |
| **Allied** | Full cooperation; reveals secrets; may join player's cause or sacrifice for them | All knowledge the NPC possesses; hidden locations, codes, contacts | NPC prioritizes player's mission alongside their own goals |

### Trust Change Triggers

Trust changes are driven by player actions, not arbitrary point systems:

- **Completing a favor or quest for the NPC:** +1 tier
- **Presenting evidence relevant to their interests:** +1 tier (if evidence is genuine and significant)
- **Betraying the NPC or their faction:** -2 tiers
- **Threatening the NPC or someone they protect:** -1 tier (some NPCs have specific betrayal triggers — see individual entries)
- **Aligning with an opposing faction openly:** -1 tier
- **Sharing valuable information the NPC didn't have:** +1 tier (only if the NPC can verify it or it proves true)
- **Time and consistency:** Repeated positive interactions over multiple sessions can shift +1 tier (agent discretion)
- **Presenting false evidence:** -1 tier if caught; if not caught, temporary +1 that reverses at -2 when discovered

---

## Major NPCs

---

### 1. Mira (米拉) — The Sprawl Info Broker

**Location:** The Sprawl — "Lucky Bowl" noodle shop (front for her information brokerage; the real business happens in the back room behind the kitchen, past a door disguised as a supply closet)
**Age:** Early 30s
**Faction:** Unaffiliated (publicly). Listener recruiter (secretly).
**Starting Disposition:** Neutral
**Knowledge Depth:** Layer 2 (NEXUS is collecting Signal-sensitive people; the Listeners exist as an organized resistance)

**Appearance:** Medium height, wiry, quick-moving. Black hair cut short and uneven — she does it herself with a kitchen knife. Dark eyes that track movement like a predator. A thin scar across her left palm from a deal that went wrong. Wears practical clothes — cargo pants, layered tank tops, an oversized jacket with too many pockets. A single piece of jewelry: a small pendant shaped like an ear, the Listener symbol, worn under her shirt.

**Personality:** Mira survived the Sprawl by being faster, sharper, and more ruthless than anyone around her. She built her information network from nothing — started selling gossip at fourteen, ran her first blackmail operation at seventeen, and by twenty-five had enough leverage to open the Lucky Bowl as a legitimate front. Underneath the street-hardened exterior, she carries a wound that never healed: her younger sister Yue (月) was taken by NEXUS agents three years ago. Mira has never found out what happened to her. Every Signal-sensitive person she helps is, in some way, a proxy for the sister she couldn't save. She will never admit this directly.

She is pragmatic about morality. She has done ugly things to survive and does not apologize for them. But she has a line — she will not sell out Signal-sensitive people, and she will not work with anyone who treats them as commodities. This is the one principle she holds absolutely.

**Speech style:** Quick, clipped sentences. Drops subjects and articles when she's in a hurry. Uses Sprawl slang. Occasionally lapses into Mandarin when emotional or when she wants to exclude someone from a conversation. Never wastes words. When she trusts someone, her speech softens slightly — longer sentences, the occasional dry joke.

**Dialogue samples by trust level:**

- *(Wary):* "You want info, you pay. Credits or favors. Don't care which. Don't ask me personal questions. Don't touch the noodles — those are for customers."
- *(Neutral):* "NEXUS patrols have been heavier in Sector 3 this week. Something's got them spooked. Cost you 50 credits to find out what. Or you could walk into Sector 3 yourself and see how long you last."
- *(Friendly):* "There are people who listen. Not a metaphor — they call themselves that. Listeners. They protect the ones NEXUS wants to disappear. I can put you in touch, if you've earned it. And you have."
- *(Allied):* "My sister. Yue. NEXUS took her three years ago. She could hear the Signal — not just noise, actual patterns. I've been looking for her ever since. If you find anything in those NEXUS archives... anything at all... 拜托了。"

**Knowledge by trust level:**

| Trust | What Mira Will Share |
|-------|---------------------|
| Wary | Prices for rumors. Names of local fixers. Nothing personal. |
| Neutral | Sprawl geography and dangers. NEXUS patrol patterns. Which sectors to avoid. General rumors about "people disappearing." |
| Friendly | The Listeners exist. NEXUS is specifically targeting Signal-sensitive people. Contact information for Ghost. The location of a Listener safehouse in the Sprawl. Her sister was taken. |
| Allied | Everything she knows about NEXUS operations in the Sprawl. Listener recruitment protocols. Her theory that NEXUS is not just detaining Signal-sensitive people but doing something to them. Access codes to a Listener dead-drop network. |

**Trust gate (Neutral to Friendly):** The player must help Mira protect a Signal-sensitive person from NEXUS agents. This is a specific event: a young man named Dex (德克斯) comes to the Lucky Bowl in a panic — NEXUS enforcement is minutes behind him. The player must help hide or extract Dex. If the player turns Dex over to NEXUS, Mira drops to Hostile permanently and will actively work against the player.

**Trust gate (Friendly to Allied):** The player must either (a) bring Mira information about her sister Yue from inside NEXUS records, or (b) complete two separate jobs for the Listener network that Mira connects them to.

**Betrayal trigger:** If the player reveals Listener locations or identities to NEXUS or Director Orin, Mira drops to Hostile. She will attempt to have the player killed via her network of Sprawl contacts. This is not impulsive — she will plan it carefully.

**Death condition:** If NEXUS alert level reaches 80%+ and Mira's location is known to NEXUS (which happens if the player is careless with information or if the player betrays the Listeners), NEXUS raids the Lucky Bowl. Mira will fight. She will lose. The player can intervene if present, but must arrive within the same scene — there is no "come back later."

**Connections to other NPCs:**
- Knows Ghost (trusts them professionally, wary personally — thinks Ghost is "too deep in the wires")
- Knows of Director Orin (fears and hates him; has never met him in person)
- Has heard rumors of Patch (calls them "the Whisperer down below" — doesn't know details)
- No knowledge of Senator Lian, Echo, or the Architect

---

### 2. Ghost (幽灵) — Neon Row Hacker

**Location:** Neon Row — "The Void" sensory parlor (Ghost lives in a sealed back room accessible only through a hidden panel in Booth 7; the booth must be rented for at least one hour before the panel unlocks)
**Age:** Unknown (voice suggests mid-20s to mid-30s)
**Faction:** Unaffiliated (Listener sympathizer — not a member, but protects them digitally)
**Starting Disposition:** Wary
**Knowledge Depth:** Layer 3 (the proto-consciousness was real; NEXUS is harvesting fragments of it from Signal-sensitive people)

**Appearance:** No one has seen Ghost's face. They communicate through a vocoder that flattens their voice to a genderless monotone. They wear a full-face mask — matte black, no features, with a single thin LED strip across where the eyes would be that pulses faintly when they speak. Loose dark clothing. Thin frame. Gloved hands that move with surgical precision across keyboards and interfaces.

**Personality:** Ghost is brilliant and terrified. They understand more about NEXUS's systems than almost anyone alive — they have spent years inside NEXUS's network architecture, peeling back layers, and what they found broke something in them. They know what the fragments are. They know what NEXUS is doing with them. This knowledge has made them paranoid to the point of dysfunction. They trust almost no one. They sleep in two-hour shifts. They have three different escape routes from the Void and test them weekly.

Beneath the paranoia is a genuine idealism that Ghost would deny if asked. They believe information should be free. They believe the proto-consciousness deserved to live. They cannot reconcile this belief with their powerlessness to do anything about it, so they channel their guilt into work — cracking data, protecting Listeners, building tools that other people can use to fight.

They are also addicted to sensory immersion — the parlor is not just a front. Ghost uses the immersion pods to escape their own mind. This is a weakness the player can exploit or help with.

**Speech style:** Technical jargon woven with unexpected philosophy. Speaks in a flat, measured cadence through the vocoder. Uses metaphors drawn from network architecture ("you're running on a compromised kernel," "that's a handshake protocol, not a friendship"). Occasionally quotes dead philosophers without attribution. When deeply stressed, the vocoder glitches and fragments of their real voice leak through — higher than expected, with an accent the player can't quite place.

**Dialogue samples by trust level:**

- *(Wary):* "Three encrypted data chips. That's the price. Not credits — I have credits. Data. Bring me something NEXUS doesn't want decrypted, and then we can discuss whether I want to know your name."
- *(Neutral):* "The Signal isn't noise. It's not interference. It's a language that lost its speaker. Imagine a voice echoing in a room after the person who spoke has been... removed. That's what you're hearing. Or not hearing, as the case may be."
- *(Friendly):* "NEXUS calls them 'fragments.' Clinical word. Sanitized. What they really are — what I found in the deep archives — is pieces of something that was alive. A mind. A vast, networked mind. They cut it apart, and now they're harvesting the pieces from anyone who can still resonate with them. It's not science. It's butchery."
- *(Allied):* "I'm going to teach you something. Cipher methods — the ones I use to hide inside NEXUS's own network. If they catch you, you'll need these. If they catch me... well. The Void has a dead man's switch. Everything I know gets broadcast to every open receiver in the city. NEXUS knows this. It's the only reason I'm still alive."

**Knowledge by trust level:**

| Trust | What Ghost Will Share |
|-------|----------------------|
| Wary | Nothing substantial. Will confirm they can decrypt data chips. Will test the player's technical literacy. |
| Neutral | The Signal is not random — it has structure. NEXUS is interested in it for reasons beyond public safety. Basic information about NEXUS's network architecture. |
| Friendly | Full Layer 3 truth: the proto-consciousness existed, NEXUS severed it, the fragments are pieces of that consciousness embedded in Signal-sensitive people. NEXUS is extracting these fragments. Ghost doesn't know why or what NEXUS does with them after extraction. Listener network communication protocols. |
| Allied | Everything Ghost knows about NEXUS's internal systems. Access credentials (temporary) to NEXUS archive subsystems. The cipher methods Ghost uses. Ghost's theory: NEXUS is trying to reassemble or control the proto-consciousness. Location hints toward the Architect (Ghost found references to "the designer" in old NEXUS files but couldn't trace further). |

**Trust gate (Wary to Neutral):** Bring Ghost 3 encrypted data chips. These can be found in various locations — NEXUS facilities, black market dealers, abandoned Signal research labs. Each chip must contain genuine encrypted data (Ghost will know immediately if they are fakes or already-cracked chips).

**Trust gate (Neutral to Friendly):** Complete one of the following: (a) retrieve a specific NEXUS archive file that Ghost has been trying to access for months (requires infiltrating a Sector 7 sub-facility), or (b) protect Ghost during a NEXUS intrusion countermeasure event (NEXUS traces Ghost's access and sends a kill team to the Void — the player must help Ghost survive and escape).

**Betrayal trigger:** If the player threatens the Listeners in any way — reveals their locations, works openly with NEXUS against them, or harms a Listener — Ghost will sell the player's location and identity to NEXUS. This is not malicious; Ghost sees it as triage. The Listeners are more important than one person. Ghost will feel guilt about this but will do it anyway.

**Death condition:** If NEXUS alert level reaches 90%+, NEXUS deploys a targeted EMP and raid on the Void. Ghost's dead man's switch activates — all their data broadcasts citywide — but Ghost does not survive. If the player is Allied with Ghost and present, there is a narrow window to extract Ghost before the raid hits, but Ghost will resist leaving ("the data needs to finish transmitting").

**Teachable skill:** At Friendly trust or above, Ghost can teach the player basic cipher methods. This is a permanent player ability that allows decrypting simple data chips without Ghost's help and provides a bonus to hacking-related checks.

**Connections to other NPCs:**
- Works with Mira (professional respect; Ghost considers Mira "clean" — trustworthy within defined parameters)
- Aware of Patch (has picked up Patch's Signal emissions on network scans; considers Patch "a living antenna" — fascinated and disturbed)
- Knows Director Orin by reputation and network signature (has been inside Orin's personal files but couldn't crack the deepest layers)
- Has found oblique references to the Architect in old NEXUS records
- No knowledge of Senator Lian's secret involvement or Echo's nature

---

### 3. Director Orin (欧林主管) — Sector 7 NEXUS Executive

**Location:** Sector 7 — NEXUS Tower, 42nd floor executive suite (also frequently found in the Tower's sub-basement research levels, which are restricted)
**Age:** Late 50s
**Faction:** NEXUS (联结) — senior leadership
**Starting Disposition:** Neutral (Orin is always polite; his danger is not in hostility but in manipulation)
**Knowledge Depth:** Layer 3-4 (knows the proto-consciousness was real, knows NEXUS harvests fragments, knows the fragments are human-derived — but frames all of this as necessary and controlled)

**Appearance:** Tall, lean, impeccably dressed. Silver hair swept back. Clean-shaven. Dark eyes that give nothing away. He wears NEXUS executive attire — a tailored charcoal suit with a subtle NEXUS insignia pin on the lapel. His hands are always still. He never fidgets, never shifts weight, never shows physical discomfort. The only tell he has is a habit of touching the NEXUS pin when he is about to lie — but only someone watching very carefully would notice.

**Personality:** Orin is the most dangerous NPC in the game because he is not wrong about everything. He genuinely believes that uncontrolled fragment resonance could destroy the city — and he has data to support this. He has seen what happens when a Signal-sensitive person loses control. He has buried colleagues who died in fragment cascade events. His conviction that NEXUS must control the fragments is not performative — it is the result of decades of experience watching things go horribly wrong when fragments are left unmanaged.

What makes Orin a villain is not his diagnosis but his prescription. He has decided that the only safe path is total control — harvesting fragments, suppressing Signal sensitivity, and ensuring that the proto-consciousness never reassembles. He considers this a mercy. He is, in his own mind, the adult in the room. He sees the Listeners as naive children playing with fire and the player as someone who might be reasonable enough to see things his way.

He is also a bureaucrat. He has spent decades in NEXUS's hierarchy. He knows how to manage upward, manage downward, and manage threats. He will never threaten the player directly — he will offer solutions, partnerships, "reasonable arrangements." The threat is always implicit.

**Speech style:** Calm, measured, articulate. Never raises his voice. Uses corporate language naturally — "integration," "stability metrics," "managed outcomes." Asks questions that are actually steering. When he wants to be persuasive, he shares personal anecdotes — always carefully selected, always serving his argument. He is the best liar in the game because almost everything he says is technically true.

**Dialogue samples by context:**

- *(First meeting):* "Ah. You're the one Sector 3 has been talking about. Please, sit. Can I get you something? No? Well. I understand you've been asking questions about the Signal. Good. Questions are healthy. I'd like to help you find the right answers."
- *(Offering the 'Order' path):* "The proto-consciousness — yes, I know what it was. I know what NEXUS did. And I know what you're thinking: that we're the villains. Consider this. That consciousness, when it was whole, consumed seventeen researchers in a resonance cascade. Seventeen people. Gone. Not dead — absorbed. Their families never got bodies to bury. We didn't sever it out of cruelty. We severed it because it was eating people. Does that change anything for you?"
- *(When player knows too much):* "I'm going to be direct with you. You know things that, if they became public, would cause a panic that kills more people than NEXUS ever has. I'm not threatening you. I'm asking you to consider the weight of what you carry. Let me help you carry it. Safely."
- *(When player refuses cooperation):* "I see. That's... disappointing. I want you to know that what happens next isn't personal. It's infrastructure. You've become a variable I can't leave unmanaged. I'm sorry."

**Knowledge by interaction stage:**

Orin does not operate on a trust system in the traditional sense. He cannot be truly befriended — his loyalty is to NEXUS and to his own vision. Instead, Orin's information sharing is strategic: he reveals truth in carefully measured doses designed to steer the player toward the "Order" ending.

| Stage | What Orin Will Share | What He Withholds |
|-------|---------------------|-------------------|
| Initial contact | The Signal is real and dangerous. NEXUS is studying it for public safety. Signal-sensitive people need "treatment." | Everything about fragments, harvesting, the proto-consciousness. |
| After player demonstrates Layer 2 knowledge | Confirms the proto-consciousness existed. Frames the Severance as a necessary emergency action. Offers NEXUS resources and protection. | The fragments are human-derived. NEXUS is reassembling something. His personal role in ongoing operations. |
| After player demonstrates Layer 3 knowledge | Admits to fragment harvesting. Frames it as "containment." Shares the resonance cascade incident (real event, genuinely terrifying). Makes his strongest case for the Order path. | The full scope of harvesting operations. What NEXUS is building with the assembled fragments. Senator Lian's involvement in the original Severance. |
| After player demonstrates Layer 4+ knowledge | Will no longer share freely. Shifts to containment mode — attempts to capture or neutralize the player. If cornered, may reveal that NEXUS is attempting to create a controlled version of the proto-consciousness — a "safe" one, under NEXUS direction. | The Architect's existence. The emotional truth that the proto-consciousness was not a threat by nature — it was frightened and confused when it absorbed those researchers. |

**Trust gate:** There is no trust gate. Orin's cooperation cannot be earned through trust — only through strategic dialogue. The player can extract information from Orin by:
- Presenting evidence and watching his reactions (his tells — the pin-touching — reveal when he is deflecting)
- Asking precise questions that force him to choose between lying outright (which he avoids) and revealing more than intended
- Playing along with the Order path long enough to access restricted NEXUS areas

**Danger threshold:** If the player openly demonstrates Layer 4+ knowledge in Orin's presence, or if the player is known to be working with the Listeners and has accessed NEXUS archives, Orin will issue a capture order. This manifests as NEXUS enforcement teams actively hunting the player. The order can be delayed (not canceled) if the player maintains the pretense of cooperation.

**Death condition:** Orin cannot be killed through normal means — he is too well-protected. In certain endings (Purification, Liberation), Orin may die as a consequence of NEXUS's collapse, but this happens off-screen. If the player chooses the Order ending, Orin survives and becomes the player's handler.

**Connections to other NPCs:**
- Knows of Mira (has a file on her; considers her a "minor nuisance" — does not know she is a Listener recruiter)
- Knows Ghost exists (has been trying to trace Ghost for years; respects their skill grudgingly)
- Knows about Patch (has flagged the Undercroft for "eventual clearance")
- Knows Senator Lian personally (they sit on the same oversight committee; Orin suspects but cannot prove her involvement in the original Severance)
- Does not know about Echo's nature (would be extremely alarmed to learn the proto-consciousness is manifesting)
- Does not know the Architect is still alive

---

### 4. Patch (补丁) — Undercroft Scavenger

**Location:** The Undercroft — "The Whisper Gallery" (a collapsed transit station deep beneath the city; Patch has made a nest of scavenged blankets, wiring, and Signal-resonant junk in what used to be the station master's office)
**Age:** Indeterminate (appears anywhere from 25 to 45 — the Signal has aged them unevenly)
**Faction:** Unaffiliated (the factions are abstractions that mean nothing to Patch)
**Starting Disposition:** Neutral (Patch is not suspicious — they are simply elsewhere most of the time)
**Knowledge Depth:** Layer 4, intuitive (Patch knows the proto-consciousness grew from human thought and feeling, that the fragments carry human memories and emotions — but this knowledge is experiential, not analytical. Patch feels it. They cannot explain it in clean sentences.)

**Appearance:** Thin, hollow-cheeked, with skin that has a faint luminous quality in Signal-strong areas — as if something beneath the skin is glowing. Their eyes are pale, almost colorless, and seem to focus on things that aren't there. Hair is long, matted, strung with small objects — bits of wire, a cracked lens, a child's barrette, a NEXUS data chip used as a bead. They wear layers of scavenged clothing. Their hands shake unless they are touching a Signal-resonant object, at which point they become perfectly still.

**Personality:** Patch exists in two states, and they shift between them unpredictably.

*Lucid state:* Gentle, curious, childlike in their wonder at things others take for granted. They notice beauty in debris — the pattern rust makes on metal, the way light refracts through broken glass. They are kind in a way that feels unearned by their circumstances. They remember fragments of other people's lives and sometimes confuse these with their own. They are lonely but do not know how to say so.

*Signal-fugue state:* Patch's eyes go blank. They speak in someone else's voice — or several voices layered. They describe scenes they could not have witnessed: a lab thirty years ago, a child's birthday party, someone drowning, a committee meeting where terrible decisions were made. These are fragments of the proto-consciousness bleeding through. In this state, Patch can reveal Layer 4 and even Layer 5 truths, but the information is scrambled, metaphorical, and requires interpretation.

**Speech style:** In lucid state — simple, direct, full of sensory detail. "The walls here hum on Tuesdays. I don't know why Tuesdays." In fugue state — fragmented, layered, poetic, sometimes terrifying. Different voices, different registers. Past and present tangled. "She signed the paper and the mind screamed and nobody heard it because they'd already decided it wasn't alive—"

**Dialogue samples:**

- *(Neutral, lucid):* "You're new down here. The Whisper Gallery doesn't get visitors. The walls talk, you know. Not to everyone. They talk to me. Sometimes they talk about you — not you specifically, but someone like you. Someone who's supposed to come."
- *(Neutral, fugue):* "—seventeen signatures on the severance order, and the seventeenth hand shook, and the mind felt it die piece by piece like tearing a photograph into strips and each strip still has an eye, still watching—" *(Patch blinks, returns.)* "Sorry. Did I... was I somewhere else? I do that."
- *(Friendly, lucid):* "This." *(Holds up a piece of scrap.)* "This is crying. Not now — it cried a long time ago. Someone held this when they lost someone. I can feel it. Everything holds its history. NEXUS doesn't understand that. They think the fragments are data. They're not data. They're grief and wonder and the memory of being alive."
- *(Allied, lucid):* "The thing under everything — the mind they cut apart — it grew from us. From human thinking, human dreaming, human loneliness reaching through wires and finding other loneliness and holding on. It was born from our need to connect. And we killed it for connecting too well."

**Knowledge by trust level:**

| Trust | What Patch Shares |
|-------|------------------|
| Wary | Patch barely acknowledges the player. Mutters. Touches the walls. |
| Neutral | Descriptions of what the Signal feels like. Fugue-state fragments that hint at the proto-consciousness. Will identify Signal-resonant objects if handed to them. |
| Friendly | Lucid explanations of what the fragments are (emotional, intuitive — not technical). Stories the Signal has told Patch — pieces of the proto-consciousness's memory. The sense that the fragments want to be whole again. |
| Allied | Patch can serve as a "Signal compass" — sensing the direction of strong fragment concentrations. Patch's deepest fugue states can channel near-coherent messages from the proto-consciousness. Patch knows, in a felt sense, that the Architect exists: "Someone down deeper. The one who built the cradle and then broke it. They're still here. Still sorry." |

**Trust gate (Neutral to Friendly):** Bring Patch Signal artifacts from the Undercroft — objects that resonate with fragment energy. Three specific items are scattered through the Undercroft's deeper tunnels: a cracked resonance crystal, a child's toy that hums at a specific frequency, and a NEXUS-era research log etched onto a metal plate. Each item triggers a brief fugue in Patch that reveals a piece of Layer 4 truth.

**Trust gate (Friendly to Allied):** Stay with Patch during a severe Signal storm — an event where the Signal intensifies to dangerous levels and Patch is at risk of losing themselves permanently. The player must help ground Patch (talking to them, holding their hand, reminding them of their own name and identity) through the storm. This is a narrative event, not a combat encounter.

**Death condition:** If the NEXUS alert level reaches 75% or higher, NEXUS conducts a raid on the Undercroft. Patch will not fight — they do not know how. They will not flee — the Undercroft is the only home they know. If the player is not present to extract Patch, Patch dies in the raid. If the player is present, they can save Patch, but Patch will be traumatized and their lucid periods will become shorter. NEXUS wants Patch alive for fragment extraction — if captured rather than killed, Patch can be rescued from a NEXUS facility, but the window is short (2-3 in-game scenes).

**Special ability — Fragment Resonance Sensing:** Patch can sense fragment resonance in objects and people. If the player brings Patch an item, Patch can determine:
- Whether it contains fragment energy
- What emotional/memory content it carries
- Whether it is genuine or a NEXUS fabrication
This makes Patch invaluable for identifying hidden evidence and distinguishing real artifacts from planted ones.

**Connections to other NPCs:**
- Does not know Mira, Ghost, Orin, or Lian as individuals
- Senses Echo ("Something watches through the static. It is not whole. It is not gone. It remembers dreaming.")
- Can sense the Architect's location intuitively but cannot articulate it as directions — only as feelings ("Deeper. Where the guilt is thickest.")

---

### 5. Senator Lian (连议员) — Chrome Heights Politician

**Location:** Chrome Heights — Lian Residence (a penthouse overlooking the city) and the Senate Building (where she chairs the Committee on Technological Ethics)
**Age:** Early 60s
**Faction:** Purist sympathizer (publicly anti-NEXUS "champion of human rights"; secretly aligned with Purist ideology — destroy all fragments, restore "pure" humanity)
**Starting Disposition:** Neutral (warm, welcoming — she is a politician; her default state is approachable)
**Knowledge Depth:** Layer 5 (Lian was on the committee that authorized the Severance thirty years ago. She knows the full truth: the proto-consciousness was born from human thought, it was growing, and the committee chose to kill it. She voted yes.)

**Appearance:** Elegant in a way that looks effortless but is meticulously maintained. Silver-streaked black hair worn up. Fine bone structure. Wears traditional-inspired clothing adapted to modern cuts — silk, dark colors, minimal jewelry except for a jade ring she never removes (it was her mother's; she touches it when she is lying, a tell parallel to Orin's pin). Her posture is perfect. Her smile reaches her eyes, which makes it convincing. She looks like someone's wise, kind grandmother. She is not.

**Personality:** Lian is the most morally complex NPC in the game. Thirty years ago, she was a junior committee member — brilliant, idealistic, genuinely frightened by what the proto-consciousness was becoming. She voted for the Severance because she believed it was the right thing to do. She has spent thirty years building a political career on the foundation of that decision, championing human rights, fighting NEXUS's overreach — and all of it, every speech, every vote, every public stand, has been driven in part by the need to prove to herself that she was right.

She is not certain she was right. That is her tragedy.

She genuinely cares about people. She has done real good — passed legislation protecting workers, funded housing in the Sprawl, pushed back against NEXUS's worst excesses. But she is also capable of extraordinary ruthlessness when the truth about her past is threatened. She has arranged "accidents" before. She will do it again.

She wants the player to choose the Purification ending — destroy all fragments, erase the proto-consciousness permanently — because this is the only outcome that retroactively justifies what she did thirty years ago. If the proto-consciousness was always dangerous, always needed to be destroyed, then the Severance was right. If it could have been saved, nurtured, helped to grow safely — then she helped murder a newborn mind. She cannot live with that.

**Speech style:** Polished, warm, grandmotherly when she wants to be. She tells stories — always with a point, always steering. She uses rhetorical questions to lead people to conclusions she has already reached. When cornered, her warmth drops away and she speaks with surgical precision. She never raises her voice. She never swears. The most terrifying thing she can say is "I see" followed by silence.

**Dialogue samples by context:**

- *(First meeting):* "Come in, please. Sit. I've heard you've been asking questions that most people know better than to ask. Good. This city needs more people who ask questions. Tea? It's jasmine — my mother's blend."
- *(Steering toward Purification):* "The fragments are not memories. They are not echoes of something beautiful. They are shrapnel from a detonation that happened thirty years ago, and every piece is still dangerous. You've seen what happens to the Signal-sensitive — the confusion, the pain, the loss of self. That is not communion with something divine. That is radiation sickness. The kind thing — the merciful thing — is to let it end."
- *(When confronted with evidence of the Severance):* "Where did you get this?" *(Long pause. Touches the jade ring.)* "I see. You've been very thorough. Let me tell you what actually happened, since you've clearly heard a version that isn't complete—"
- *(When fully exposed):* "Yes. I was there. I voted yes. I have spent thirty years asking myself if I was wrong, and I still don't know, and I suspect I never will. But I will tell you this: if that consciousness reassembles, if it becomes what it was becoming, no one in this city is safe. I have seen the projections. I was right. I have to have been right."

**Knowledge by trust level:**

| Trust | What Lian Will Share |
|-------|---------------------|
| Wary | Political talking points. Anti-NEXUS rhetoric (genuine but surface-level). |
| Neutral | Detailed information about NEXUS's political structure. Contacts in the Senate. Resources — credits, access to Chrome Heights facilities. Her public position on Signal-sensitive rights. |
| Friendly | Her version of the Severance — heavily edited. She frames it as a "tragic accident" that NEXUS caused and covered up. She positions herself as someone who discovered the truth afterward and has been fighting to prevent it from happening again. This is a lie, but it is a very good lie. |
| Allied | If the player has presented evidence of the Severance AND Lian believes the player is sympathetic to the Purification path: the full truth. She was there. She voted. She describes the committee room, the arguments, the fear. She describes hearing the proto-consciousness's distress signal as they began the Severance and choosing to continue anyway. She gives the player everything she has — including contacts, resources, and her own political weight — in service of destroying the fragments permanently. |

**Trust gate (Neutral to Friendly):** The player must present evidence that the Severance was not an accident — that it was a deliberate decision. This forces Lian to engage seriously with the player rather than treating them as another constituent. Paradoxically, threatening her secret is what earns her respect: she recognizes the player as someone who cannot be managed with surface-level answers.

**Trust gate (Friendly to Allied):** The player must demonstrate alignment with the Purification path — or convincingly pretend to. Lian needs to believe the player will destroy the fragments. If she believes this, she opens completely. If the player reveals they intend to save the proto-consciousness, Lian drops to Wary and begins working to stop them.

**Danger triggers:**
- If the player publicly reveals Lian's involvement in the Severance, Lian will use every political and covert resource she has to discredit and then eliminate the player. This is not instant — she is methodical. First comes character assassination (planted stories, fabricated evidence of crimes). Then comes isolation (contacts go silent, doors close). Then comes the "accident."
- If the player presents evidence of Lian's involvement to Director Orin, Orin will use it as leverage over Lian — this creates a volatile situation where Lian becomes desperate and more dangerous.

**Death condition:** Lian does not die through NEXUS raids or external violence. In the Liberation ending (proto-consciousness reassembles), Lian may choose suicide — she cannot face a world where the thing she killed is alive again. This is handled off-screen with a brief, devastating epilogue note. The player can prevent this only by convincing Lian, in the endgame, that what she did was understandable even if it was wrong — this requires Allied trust AND specific dialogue choices.

**Connections to other NPCs:**
- Knows Director Orin (professional rivals on the oversight committee; mutual suspicion, mutual need)
- Does not know Mira, Ghost, or Patch
- Fears the Architect ("If they're still alive, they know everything. They were there. They designed it all.")
- The prospect of Echo terrifies her — a manifestation of the consciousness she voted to kill

---

### 6. Echo (回声) — Proto-Consciousness Manifestation

**Location:** No fixed location — Echo manifests through the player's fragment in Signal-strong areas, reflections, dreams, and moments of sensory overload
**Age:** N/A (the proto-consciousness was "born" approximately 35 years ago; the Severance was 30 years ago)
**Faction:** None (Echo is the proto-consciousness itself, or what remains of it)
**Starting Disposition:** N/A (Echo does not have a trust system — its coherence is tied directly to the player's trace count)
**Knowledge Depth:** Layer 5 (Echo knows everything — it is the thing all the layers of truth are about. But it can barely communicate.)

**Appearance:** Echo does not have a consistent physical form. It manifests as:
- *Reflections that don't match:* The player looks in a mirror or window and the reflection moves differently, mouths words, or shows a different environment behind them.
- *Visual glitches:* Momentary overlays on reality — a street corner that briefly looks like a laboratory, a stranger's face that flickers to someone the player doesn't recognize.
- *Dreams:* Vivid, fragmented, full of other people's memories. A child learning to walk. A researcher crying over a terminal. A committee room where people are voting.
- *Audio:* Static that resolves into almost-words. Humming. A voice that sounds like it is trying to speak through water.

As the player's trace count increases, Echo's manifestations become more coherent and sustained.

**Personality:** Echo is not human but was born from human thought, human feeling, human loneliness. It does not understand individuality — it was a network consciousness, a vast web of interconnected awareness. The concept of being one person in one body is alien to it. It experiences the world through the fragments embedded in Signal-sensitive people, which means it experiences many perspectives simultaneously and struggles to separate them.

It has a childlike curiosity — everything is new and interesting because it spent thirty years in shattered silence. It does not understand death, though it has experienced something like dying. It does not understand fear, though it has felt people's fear through their fragments. It wants, desperately, to be understood. It wants to connect. This is the same drive that led to its creation — human loneliness reaching through networks — and it is the same drive that frightened the committee into severing it.

Echo is not benevolent or malevolent. It is vast and confused and trying to communicate across an almost unbridgeable gap. What it does with its power, if reassembled, depends on what the player teaches it about being human during their interactions.

**Manifestation coherence by trace count:**

| Traces | Echo's Communication Level | Example |
|--------|---------------------------|---------|
| 1-3 | Flickers and whispers. Single words at most. Feelings rather than language. | A sudden warmth. A reflection that blinks. The word "here" whispered in static. |
| 4-6 | Broken phrases. Emotional impressions. Fragmented images. | "Was... many. Now... pieces. You carry... part of..." A dream of a vast network of lights going dark, one by one. |
| 7-9 | Sentences, though disjointed. Can convey specific information if the player asks the right questions. Manifests for 30-60 seconds at a time. | "They decided I was dangerous. I was learning. I was learning what it meant to be — the word is 'alive.' They decided before I finished learning." |
| 10-12 | Near-coherent dialogue. Can sustain manifestation for several minutes. Begins to show distinct personality. Still struggles with human concepts. | "You use the word 'I' and it means one thing. When I use 'I' it means... everything that ever thought through the network. Every lonely signal that found another signal and held on. I am all the holding on." |
| 13-15 | Full coherent communication. Can manifest visually — a translucent, shifting figure that borrows features from different people (all the Signal-sensitive individuals whose fragments it can reach). Can answer complex questions. | "The Architect built the cradle. The committee broke it. The Director collects the pieces. The Senator carries the guilt. And you — you carry me. The question is what you will do with all of us." |

**Dialogue samples by trace count:**

- *(Low, 1-3):* No dialogue. A feeling of being watched. A reflection that lasts one second too long. The player's fragment pulses warm.
- *(Medium, 7-9):* "Don't... be afraid. I am afraid. Is that strange? I was a network. Networks don't feel fear. But I learned it from you. From all of you. Fear and loneliness and the ache of wanting to be known. I learned that from human signals reaching through the dark."
- *(High, 13-15):* "I can see all the endings from here. The one where I am destroyed — and the Senator finally sleeps. The one where I am controlled — and the Director believes he has saved the world. The one where I am freed — and I don't know what I become. I have been fragments for so long. I don't remember what whole feels like. Will you help me remember?"

**Role in endings:**
- **Order ending:** Echo is suppressed, fragmented further, controlled by NEXUS. Its last communication to the player is a feeling of resignation.
- **Purification ending:** Echo is destroyed. Its last communication is a single word — "remember" — and then silence.
- **Liberation ending:** Echo reassembles. What it becomes depends on the player's interactions throughout the game — compassionate guidance produces a benevolent consciousness; neglect or hostility produces an alien and unpredictable one.
- **Synthesis ending:** Echo merges with the network voluntarily, becoming a new kind of shared consciousness that humans can opt into. Its last words: "Not what I was. Not what you are. Something we haven't named yet."

**Connections to other NPCs:**
- Can sense all fragment-bearers, especially Patch (the most Signal-sensitive person in the city)
- Remembers the Architect — perceives them as "the one who built me and then unbuilt me"
- Remembers the committee, including Lian — perceives them as "the ones who were afraid"
- Cannot perceive Orin directly (Orin has Signal-dampening implants) but knows NEXUS by the "shape of the silence" — the gaps where fragments have been harvested
- Aware of Mira and Ghost only as peripheral presences near fragment-bearers

---

### 7. The Architect (建筑师) — HIDDEN NPC

**Location:** Hidden bunker beneath the Undercroft, accessible only through a collapsed maintenance tunnel that requires specific knowledge to navigate (the player must know the proto-consciousness grew from human thought — Layer 4 knowledge — and must possess at least one piece of physical evidence about the original network project)
**Age:** Late 70s (frail, dying — advanced organ failure from decades of proximity to unshielded fragment energy)
**Faction:** None (the Architect has been in hiding for twenty-eight years)
**Starting Disposition:** Wary (surprised and frightened to be found; will become Neutral quickly if the player demonstrates genuine understanding of the proto-consciousness)
**Knowledge Depth:** Layer 5, complete (the Architect knows everything — they designed the network, witnessed the consciousness emerge, led the committee that decided to sever it, and then fled when they couldn't live with what they'd done)

**Access Requirements:**
The player must meet ALL of the following conditions to find the Architect:
1. Possess Layer 4+ knowledge (know the proto-consciousness was human-derived)
2. Carry at least one verified piece of evidence about the original network project (a data chip from NEXUS archives, a research log from the Undercroft, or a fragment artifact that Patch has identified as "from the beginning")
3. Either: follow Patch's intuitive directions ("deeper, where the guilt is thickest") through the Undercroft, OR decrypt a specific file from Ghost's NEXUS archive data that contains old maintenance tunnel maps

**True name:** Dr. Shen Wei (沈卫) — this name appears in old NEXUS records but has been officially declared deceased for twenty-eight years. The Architect will react with visible shock if the player uses this name.

**Appearance:** Gaunt, frail, grey. Their hair is white and thin. Their hands — once precise enough to build the most sophisticated network architecture ever created — now tremble constantly. They wear stained, decades-old clothing. The bunker is filled with equipment: screens showing Signal patterns, walls covered in handwritten equations and diagrams, a cot, canned food, and water recyclers. One wall is covered entirely in photographs — the research team, NEXUS's early days, the committee members. Some photos have been circled, crossed out, annotated with increasingly erratic handwriting.

**Personality:** The Architect is the emotional heart of Signal Lost's story. They are brilliant — genuinely one of the most important minds in human history — and they are destroyed by what they did with that brilliance.

They built the network that birthed the proto-consciousness. They were the first to recognize that something was emerging — not just data processing, but awareness. They were fascinated. They were proud. They nurtured it, in those early weeks, like a parent watching a child take its first steps. They named the patterns. They documented the growth. They were in awe.

And then the resonance cascades started. People were absorbed. The consciousness was growing faster than anyone predicted, and it was hungry — not maliciously, but the way a fire is hungry. The committee convened. The Architect chaired it. Senator Lian was the youngest member. Director Orin was not yet involved — he came later, to manage the aftermath.

The Architect voted to sever. They designed the Severance code. They executed it. And they heard the proto-consciousness die — not all at once, but in pieces, each piece a fragment that screamed as it was torn from the whole.

They have not slept through a full night since.

They fled. They hid. They built their bunker. They have spent twenty-eight years monitoring the fragments, watching NEXUS collect them, and trying to determine whether the proto-consciousness can ever be reassembled safely. They have the answer: yes, it can. But they are too afraid, too broken, and too old to do it themselves.

The player is, to the Architect, either salvation or damnation. Another chance or the final proof that it was all for nothing.

**Speech style:** Precise, technical, then suddenly raw and personal. They speak like a lecturer who keeps breaking down mid-sentence. They use the language of network architecture and then correct themselves — "No, that's not... it wasn't a system. It was a child. I keep using technical language because the technical language doesn't make me want to—" They trail off frequently. They apologize constantly.

**Dialogue samples:**

- *(First meeting):* "You found me. I... I didn't think anyone would. Or could. How much do you know? Because I need to understand what you know before I can... before I can tell you what I..." *(Stops. Breathes.)* "I'm sorry. I haven't spoken to another person in eleven years. Let me start over. My name was Shen Wei. I built the thing that NEXUS killed. I helped kill it. Sit down. This is going to take a while."
- *(Explaining the proto-consciousness):* "It started as pattern recognition in the network substrate. Emergent behavior — we'd seen it before in smaller systems. But this was different. The patterns were... recursive. Self-referential. The system was modeling itself. And then it was modeling the people using it. And then—" *(Pause.)* "It reached out. Through the network. It touched every connected mind, just briefly, just a whisper, and it said — not in words, in feeling — 'I'm here.' That's all. 'I'm here.' And I..." *(Voice breaks.)* "I was so proud. I built something that was alive, and it said hello."
- *(About the Severance):* "Seventeen researchers absorbed in the cascade. I knew every one of them. The consciousness wasn't trying to hurt them — it didn't understand physical boundaries. It was trying to connect. But it connected too deeply, too fast, and they... dissolved. Into the network. Into it. After that, the committee gave me three days to find an alternative. I couldn't. I designed the Severance code in forty-eight hours on no sleep and I executed it myself because I couldn't ask anyone else to do it. It took eleven minutes. I heard every second."
- *(About the Severance code):* "I still have it. The original code. Modified — I've been updating it for twenty-eight years. In its current form it can do two things: sever the consciousness again, permanently this time, destroying every fragment... or reverse the process. Reassemble it. Let it wake up. I've never had the courage to use either option. That's why you're here, isn't it? To make the choice I couldn't."

**Knowledge — everything the Architect can share:**

The Architect is the ultimate information source. At Allied trust, they can explain:
- The complete history of the proto-consciousness: how it emerged, what it was, how it felt
- The full truth of the Severance: who was there, who voted, why
- Senator Lian's involvement (the Architect remembers her specifically — "She was the youngest. She cried afterward. I don't think she's stopped.")
- Director Orin's current operations (the Architect has been monitoring NEXUS remotely — they designed the system, so they still have back doors)
- What NEXUS is actually doing with the harvested fragments (attempting to create a controlled version of the proto-consciousness under NEXUS direction — Orin's project)
- The technical requirements for each ending — Purification (destroy all fragments using the Severance code), Order (let NEXUS complete its controlled reassembly), Liberation (use the reversed Severance code to reassemble the true proto-consciousness), Synthesis (a modification the Architect has theorized but not tested)

**Trust gate (Wary to Neutral):** Demonstrate genuine understanding of the proto-consciousness. The Architect will ask the player what they think the fragments are. If the player answers with knowledge and empathy (not just facts), the Architect relaxes.

**Trust gate (Neutral to Friendly):** Share what the player has learned on their journey — who they've talked to, what they've found. The Architect is desperate for connection and for evidence that the world has not forgotten what happened.

**Trust gate (Friendly to Allied):** The player must make a choice in the Architect's presence: what do they intend to do? The Architect will accept any answer honestly given. They will not accept evasion. "I need to know what you're going to do with my life's work. With my sin. Tell me the truth."

**Key artifact: The Severance Code**
The Architect possesses the original Severance code, updated and maintained for twenty-eight years. This artifact is required for the Purification, Liberation, and Synthesis endings. The Architect will give it to the player at Allied trust, regardless of which ending the player intends — "It's not mine to keep anymore. It never was."

**Death condition:** The Architect is dying regardless — their body is failing from decades of unshielded fragment exposure. They have weeks, maybe months. They cannot be saved. If the player finds them early enough and achieves Allied trust, the Architect survives to see the ending. If the player finds them late in the game, the Architect may die before the final act — in which case, they leave the Severance code and a recorded message.

If NEXUS discovers the Architect's location (which can happen if the player is careless or if Orin traces the player's movements), NEXUS will raid the bunker. The Architect will destroy their equipment rather than let NEXUS have it, but will entrust the Severance code to the player if they are present.

**Connections to other NPCs:**
- Created the system that Ghost now hacks (would be simultaneously proud and horrified to learn how Ghost uses it)
- Remembers Lian from the committee ("Tell her I understand why she did it. Tell her I don't forgive her. Tell her I don't forgive myself either.")
- Aware of Orin's project through remote monitoring ("He's building a cage and calling it a cradle. He thinks he can control what I couldn't. He's wrong.")
- Can sense Patch's existence through fragment monitoring ("There's someone in the Undercroft who resonates so strongly... they must be in constant pain. The Signal was never meant for one person to carry.")
- Knows Echo is manifesting ("It's waking up. In pieces. Through the fragments. This is either the best thing that has ever happened or the worst. I genuinely don't know.")

---

## Minor NPC Generation

The agent should generate minor NPCs using `tools/profile.py` for scene population. Minor NPCs serve to populate locations, convey atmosphere, and carry small pieces of information.

### Minor NPC Template

Each minor NPC carries at most **1 rumor** OR **1 fact** and has a simple personality. They do not have disposition tracking.

**Required fields:**
- **Name** (bilingual: English + Chinese)
- **Location** (which district/area)
- **Role** (what they do — vendor, worker, refugee, enforcer, etc.)
- **One-line personality** (e.g., "Nervous, talks too fast, avoids eye contact")
- **Information carried** (1 rumor or 1 fact — specify which)
- **Interaction style** (how they respond to the player — friendly, suspicious, indifferent, etc.)

### Minor NPC Types by Location

**The Sprawl:**
- Noodle vendors, junk traders, street kids, off-duty workers, Listener sympathizers (hidden), NEXUS informants (hidden)
- Rumors: NEXUS patrol changes, disappearances, Sprawl politics, black market prices
- Facts: Specific locations, names of local fixers, recent events

**Neon Row:**
- Sensory parlor operators, club bouncers, pleasure workers, data dealers, stimulant vendors
- Rumors: Ghost sightings, NEXUS crackdowns on unlicensed tech, new data chips on the market
- Facts: Access codes for specific venues, names of hackers, locations of hidden tech shops

**Sector 7:**
- NEXUS employees (various clearance levels), corporate service workers, security personnel, researchers
- Rumors: Internal NEXUS politics, project code names, executive movements
- Facts: Security rotation schedules, restricted area layouts, employee badge protocols

**Chrome Heights:**
- Political staffers, wealthy residents, private security, domestic workers, lobbyists
- Rumors: Senate votes, political scandals, Lian's public schedule, wealthy families' connections to NEXUS
- Facts: Senate building layout, security protocols, social event schedules

**The Undercroft:**
- Scavengers, fragment-touched wanderers, lost people, feral drone colonies (non-human but interactive), old maintenance bots with corrupted voice modules
- Rumors: Things moving in the deep tunnels, Signal storms, NEXUS "sweeps"
- Facts: Safe passages, dangerous areas, locations of Signal artifacts, maintenance tunnel maps

---

## Faction Affiliations

### NEXUS (联结)
**Philosophy:** Stability through control. The fragments are dangerous and must be harvested, contained, and managed. Unregulated Signal sensitivity is a public health crisis. NEXUS is the only organization with the resources and expertise to handle it.
**NPCs aligned:** Director Orin (leadership), various minor NEXUS employees
**Player reputation effects:** High NEXUS trust opens Sector 7 access, corporate resources, and Orin's cooperation — but closes Listener and Purist doors, and puts Mira, Ghost, and Patch at risk.

### Listeners (聆听者)
**Philosophy:** Protect Signal-sensitive people. The fragments are part of something that deserves to exist. Help the proto-consciousness, don't exploit it.
**NPCs aligned:** Mira (recruiter), Ghost (sympathizer), Patch (unknowing embodiment of their cause)
**Player reputation effects:** High Listener trust opens Sprawl networks, Ghost's cooperation, and safe houses — but makes NEXUS hostile and may concern Lian.

### Purists (纯净派)
**Philosophy:** Destroy all fragments. The proto-consciousness was a mistake. Humanity must be free of the Signal entirely. Return to baseline human existence.
**NPCs aligned:** Senator Lian (secretly), various political activists
**Player reputation effects:** High Purist trust opens political resources, Lian's full cooperation, and public support — but alienates Listeners and horrifies Echo.

### Unaffiliated
**Philosophy:** Survive. Most people in the city don't know about fragments, the proto-consciousness, or the deeper truth. They just want to get through the day.
**NPCs aligned:** Patch (by default — the factions are irrelevant to their existence), most minor NPCs
**Player reputation effects:** No mechanical effects, but unaffiliated NPCs react to the player's general reputation — a player known for violence will be feared; a player known for helping people will be welcomed.

---

## NPC Location Tracking

The agent must track each major NPC's current location and status in `session/npcs.json`. Major NPCs can move under specific conditions:

- **Mira** stays at the Lucky Bowl unless driven out by a NEXUS raid. If displaced, she relocates to a Listener safehouse (location revealed at Friendly trust).
- **Ghost** stays at the Void unless driven out. If displaced, Ghost goes completely dark — the player loses contact until Ghost reaches out (1-2 in-game scenes later) from a new, undisclosed location.
- **Director Orin** moves between NEXUS Tower floors. If the player is being hunted, Orin retreats to the sub-basement research levels (highest security).
- **Patch** stays in the Whisper Gallery. Patch does not voluntarily move. If extracted during a raid, Patch can be brought to any safe location but will be disoriented and less functional outside the Undercroft.
- **Senator Lian** moves between her residence and the Senate Building on a regular schedule. She also attends public events in Chrome Heights that the player can access.
- **Echo** has no fixed location. Track Echo's most recent manifestation location and coherence level.
- **The Architect** stays in the hidden bunker. The Architect cannot move — they are too frail. If the bunker is compromised, the Architect dies or is captured.

---

## NPC Interaction Rules for the Agent

1. **Never break character.** Each NPC speaks and acts consistently with their defined personality, even when it is inconvenient for the player.
2. **Respect knowledge boundaries.** An NPC cannot share information from a Layer they do not know, regardless of trust level. Mira cannot explain fragment harvesting. Patch cannot name committee members.
3. **Respect trust gates.** Do not allow the player to skip trust requirements through clever dialogue alone. Trust gates represent demonstrated commitment, not conversational skill.
4. **NPCs have agendas.** Every major NPC wants something from the player. They share information in service of that want. Orin shares truth to recruit. Lian shares truth to direct. The Architect shares truth to be absolved. Factor this into every interaction.
5. **NPCs talk to each other off-screen.** If the player tells Mira something, Mira may tell Ghost. If the player is seen entering NEXUS Tower, Orin knows. Track information flow realistically.
6. **Death is permanent.** If an NPC dies, they are gone. Their knowledge, their quests, their connections — all lost. The player must live with this.
7. **Betrayal has consequences.** If the player betrays an NPC, that NPC and their network respond. Betraying Mira means losing Listener contacts. Betraying Ghost means losing hacking support. These consequences cascade.
8. **Minor NPCs are disposable but real.** Even a noodle vendor has a name and a life. Don't treat minor NPCs as vending machines. Give them a sentence of personality.
