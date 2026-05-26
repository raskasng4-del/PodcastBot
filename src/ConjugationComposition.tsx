import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  useVideoConfig,
  Easing,
  Sequence,
  Audio,
  staticFile,
} from "remotion";

const VERB_EMOJIS: Record<string, string> = {
  être: "💫", avoir: "🎯", parler: "🗣️", manger: "🍔",
  finir: "✅", dormir: "😴", courir: "🏃", lire: "📖",
  écrire: "✍️", chanter: "🎤", danser: "💃", jouer: "🎮",
  boire: "🍷", prendre: "📸", mettre: "👕", venir: "🚶",
  voir: "👀", savoir: "🧠", pouvoir: "💪", vouloir: "🎯",
  devoir: "📋", falloir: "⚠️", pleuvoir: "🌧️", aller: "🏃",
  faire: "🛠️", dire: "💬", partir: "✈️", sortir: "🚪",
  attendre: "⏳", répondre: "📩", vendre: "🏪", entendre: "👂",
  perdre: "🔍", sentir: "👃", ouvrir: "🚪", souffrir: "💔",
  offrir: "🎁", cueillir: "🌺", craindre: "😨", peindre: "🎨",
  joindre: "🔗", connaître: "🔍", disparaître: "👻", naître: "👶",
  croire: "🙏", rire: "😂", suivre: "👣", vivre: "🌟",
  conduire: "🚗", construire: "🏗️", détruire: "💥", traduire: "🌍",
  cuire: "🍳", dire: "📢", écrire: "📝", lire: "📚",
  plaire: "😊", taire: "🤫", suffire: "✅", conclure: "🔚",
  exclure: "🚫", inclure: "📥", résoudre: "🧩", absoudre: "🙏",
  dissoudre: "💧", moudre: "⚙️", coudre: "🧵", battre: "⚔️",
  mettre: "📦", promettre: "🤝", permettre: "✅", commettre: "❌",
  transmettre: "📡", rompre: "💔", corrompre: "💰", vaincre: "🏆",
  convaincre: "🤝", peindre: "🖌️", craindre: "😰", plaindre: "😢",
  joindre: "🔗", astreindre: "⚖️", feindre: "🎭", geindre: "😩",
  éteindre: "🔌", étreindre: "🤗", atteindre: "🎯", ceindre: "👑",
  enfreindre: "🚫", restreindre: "🔒", teindre: "🎨", repeindre: "🔄",
};

const FALLBACK_EMOJIS = ["⭐", "✨", "🔥", "💫", "🎯", "🌟", "⚡", "💡"];

function getVerbEmoji(verb: string): string {
  const key = verb.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  for (const [vk, emoji] of Object.entries(VERB_EMOJIS)) {
    if (key === vk || key.includes(vk)) return emoji;
  }
  let hash = 0;
  for (let i = 0; i < key.length; i++) {
    hash = (hash * 31 + key.charCodeAt(i)) | 0;
  }
  return FALLBACK_EMOJIS[Math.abs(hash) % FALLBACK_EMOJIS.length];
}

const gradients = [
  "linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%)",
  "linear-gradient(135deg, #1a0a2e 0%, #2d1b69 50%, #1b1464 100%)",
  "linear-gradient(135deg, #0d0d1a 0%, #1a1a4e 50%, #0a0a2e 100%)",
  "linear-gradient(135deg, #100e1e 0%, #2a205a 50%, #1e1646 100%)",
];

function getGradient(verb: string): string {
  let hash = 0;
  for (let i = 0; i < verb.length; i++) {
    hash = (hash * 31 + verb.charCodeAt(i)) | 0;
  }
  return gradients[Math.abs(hash) % gradients.length];
}

const PRONOUN_LABELS: Record<string, string> = {
  je: "Je", tu: "Tu", "il/elle": "Il/Elle",
  nous: "Nous", vous: "Vous", "ils/elles": "Ils/Elles",
};

interface TimelineEntry {
  pronoun: string;
  conjugation: string;
  audioSrc: string;
  startFrame: number;
  durationInFrames: number;
}

interface VerbData {
  infinitive: string;
  level: string;
}

export interface ConjugationProps {
  verb: VerbData;
  tense: string;
  timeline: TimelineEntry[];
  totalDuration: number;
}

const TenseLabel: React.FC<{ tense: string }> = ({ tense }) => {
  const labels: Record<string, string> = {
    present: "Présent de l'indicatif",
    passe_compose: "Passé composé",
    imparfait: "Imparfait",
  };
  return (
    <span
      style={{
        fontSize: 20,
        fontWeight: 400,
        color: "rgba(255,255,255,0.5)",
        letterSpacing: 2,
        textTransform: "uppercase",
      }}
    >
      {labels[tense] || tense}
    </span>
  );
};

const VerbHeader: React.FC<{ infinitive: string; tense: string }> = ({
  infinitive,
  tense,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const emoji = getVerbEmoji(infinitive);

  const opacity = interpolate(frame, [0, fps * 0.5], [0, 1], {
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  const y = interpolate(frame, [0, fps * 0.5], [-30, 0], {
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 8,
        opacity,
        transform: `translateY(${y}px)`,
        marginBottom: 40,
      }}
    >
      <span style={{ fontSize: 56 }}>{emoji}</span>
      <span
        style={{
          fontFamily: "Arial, Helvetica, sans-serif",
          fontSize: 64,
          fontWeight: 800,
          color: "#ffffff",
          textShadow: "0 4px 30px rgba(0,0,0,0.5)",
          letterSpacing: 2,
        }}
      >
        {infinitive.toUpperCase()}
      </span>
      <TenseLabel tense={tense} />
    </div>
  );
};

const ConjugationLine: React.FC<{
  pronoun: string;
  conjugation: string;
  index: number;
  isActive: boolean;
  animateIn: boolean;
}> = ({ pronoun, conjugation, index, isActive, animateIn }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const label = PRONOUN_LABELS[pronoun] || pronoun;

  const entryDelay = index * 3;
  const entryOpacity = animateIn
    ? interpolate(frame, [entryDelay, entryDelay + fps * 0.4], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: Easing.bezier(0.16, 1, 0.3, 1),
      })
    : 1;

  const activeScale = isActive
    ? interpolate(frame % 60, [0, 15, 60], [1, 1.08, 1.08], {
        extrapolateRight: "clamp",
        easing: Easing.bezier(0.16, 1, 0.3, 1),
      })
    : 1;

  const leftGlow =
    isActive && pronoun !== "je" && pronoun !== "tu"
      ? interpolate(
          frame,
          [
            Math.max(0, (frame - 30) % 60),
            Math.max(0, (frame - 30) % 60 + 10),
          ],
          [0, 1],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
        )
      : 0;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 16,
        padding: "10px 28px",
        margin: 4,
        borderRadius: 12,
        backgroundColor: isActive
          ? "rgba(0, 212, 255, 0.12)"
          : "transparent",
        transform: `scale(${activeScale})`,
        opacity: entryOpacity,
        transition: undefined,
        borderLeft: isActive ? "3px solid #00d4ff" : "3px solid transparent",
        boxShadow: isActive
          ? "0 0 30px rgba(0, 212, 255, 0.15)"
          : "none",
      }}
    >
      <span
        style={{
          fontFamily: "Arial, Helvetica, sans-serif",
          fontSize: 28,
          fontWeight: isActive ? 700 : 500,
          color: isActive ? "#00d4ff" : "rgba(255,255,255,0.5)",
          minWidth: 80,
          textAlign: "right",
          textShadow: isActive
            ? "0 0 20px rgba(0, 212, 255, 0.3)"
            : "none",
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontFamily: "Arial, Helvetica, sans-serif",
          fontSize: 32,
          fontWeight: isActive ? 700 : 400,
          color: isActive ? "#ffffff" : "rgba(255,255,255,0.45)",
          minWidth: 160,
          textAlign: "left",
          textShadow: isActive
            ? "0 0 20px rgba(0, 212, 255, 0.2)"
            : "none",
        }}
      >
        {conjugation}
      </span>
    </div>
  );
};

const Branding: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const opacity = interpolate(
    frame,
    [Math.max(0, fps * 3), fps * 4],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const pulse = Math.sin((frame / fps) * Math.PI * 0.5) * 0.15 + 0.85;

  return (
    <div
      style={{
        position: "absolute",
        bottom: 60,
        opacity,
        transform: `scale(${pulse})`,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 4,
      }}
    >
      <span
        style={{
          fontFamily: "Arial, Helvetica, sans-serif",
          fontSize: 18,
          fontWeight: 700,
          color: "rgba(255,255,255,0.3)",
          letterSpacing: 3,
          textTransform: "uppercase",
        }}
      >
        French Flow
      </span>
      <div
        style={{
          width: 40,
          height: 2,
          backgroundColor: "rgba(255,255,255,0.15)",
          borderRadius: 1,
        }}
      />
    </div>
  );
};

export const ConjugationComposition: React.FC<ConjugationProps> = ({
  verb,
  tense,
  timeline,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const bgOpacity = interpolate(frame, [0, fps * 0.3], [0, 1], {
    extrapolateRight: "clamp",
  });

  const activeIndex = timeline.findIndex(
    (t) => frame >= t.startFrame && frame < t.startFrame + t.durationInFrames,
  );

  const pronounOrder = ["je", "tu", "il/elle", "nous", "vous", "ils/elles"];
  const uniquePronouns = [
    ...new Set(timeline.map((t) => t.pronoun)),
  ];
  const sortedPronouns = pronounOrder.filter((p) =>
    uniquePronouns.includes(p),
  );

  return (
    <AbsoluteFill
      style={{
        background: getGradient(verb.infinitive),
        opacity: bgOpacity,
      }}
    >
      {timeline.map((entry, i) => (
        <Sequence
          key={`audio-${i}`}
          from={entry.startFrame}
          durationInFrames={entry.durationInFrames}
        >
          <Audio src={staticFile(entry.audioSrc)} />
        </Sequence>
      ))}

      <AbsoluteFill
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "60px 40px",
        }}
      >
        <VerbHeader infinitive={verb.infinitive} tense={tense} />

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 6,
          }}
        >
          {sortedPronouns.map((pronoun) => {
            const entry = timeline.find((t) => t.pronoun === pronoun);
            if (!entry) return null;
            const idx = sortedPronouns.indexOf(pronoun);
            const isActive = activeIndex >= 0 && timeline[activeIndex]?.pronoun === pronoun;
            return (
              <ConjugationLine
                key={pronoun}
                pronoun={pronoun}
                conjugation={entry.conjugation}
                index={idx}
                isActive={isActive}
                animateIn={frame < fps * 2}
              />
            );
          })}
        </div>
      </AbsoluteFill>

      <Branding />
    </AbsoluteFill>
  );
};
