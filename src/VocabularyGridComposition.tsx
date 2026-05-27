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

interface VocabularyWord {
  french: string;
  english: string;
  emoji: string;
  audioSrc: string;
}

interface TimelineEntry {
  wordIndex: number;
  startFrame: number;
  durationInFrames: number;
}

export interface VocabularyGridProps {
  title: string;
  words: VocabularyWord[];
  bgMusicSrc?: string;
  timeline?: TimelineEntry[];
  totalDuration?: number;
}

const ACTIVE_BORDER = "#00d4ff";

const TitleBar: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const opacity = interpolate(frame, [0, fps * 0.5], [0, 1], {
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  const y = interpolate(frame, [0, fps * 0.5], [-20, 0], {
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  return (
    <div
      style={{
        fontFamily: "Arial, Helvetica, sans-serif",
        fontSize: 38,
        fontWeight: 800,
        color: "#1a1a2e",
        textAlign: "center",
        opacity,
        transform: `translateY(${y}px)`,
        marginBottom: 32,
        letterSpacing: 1,
      }}
    >
      {text}
    </div>
  );
};

const VocabularyCell: React.FC<{
  word: VocabularyWord;
  index: number;
  isActive: boolean;
}> = ({ word, index, isActive }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const entryDelay = index * 4;
  const entryOpacity = interpolate(
    frame,
    [entryDelay, entryDelay + fps * 0.3],
    [0, 1],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.16, 1, 0.3, 1),
    },
  );

  const activeScale = isActive
    ? interpolate(frame % 30, [0, 10, 30], [1, 1.05, 1.05], {
        extrapolateRight: "clamp",
        easing: Easing.bezier(0.16, 1, 0.3, 1),
      })
    : 1;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 8,
        padding: "20px 10px",
        borderRadius: 16,
        backgroundColor: "#ffffff",
        boxShadow: isActive
          ? "0 8px 30px rgba(0, 212, 255, 0.2)"
          : "0 4px 20px rgba(0,0,0,0.06)",
        border: isActive
          ? `2px solid ${ACTIVE_BORDER}`
          : "2px solid transparent",
        transform: `scale(${activeScale})`,
        opacity: entryOpacity,
      }}
    >
      <span style={{ fontSize: 44, lineHeight: 1 }}>{word.emoji}</span>
      <span
        style={{
          fontFamily: "Arial, Helvetica, sans-serif",
          fontSize: 26,
          fontWeight: 700,
          color: "#1a1a2e",
          textAlign: "center",
        }}
      >
        {word.french}
      </span>
      <span
        style={{
          fontFamily: "Arial, Helvetica, sans-serif",
          fontSize: 16,
          fontWeight: 400,
          color: "#6b7280",
          textAlign: "center",
        }}
      >
        {word.english}
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

  return (
    <div
      style={{
        position: "absolute",
        bottom: 40,
        left: 0,
        right: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 4,
        opacity,
      }}
    >
      <span
        style={{
          fontFamily: "Arial, Helvetica, sans-serif",
          fontSize: 14,
          fontWeight: 700,
          color: "rgba(0,0,0,0.2)",
          letterSpacing: 3,
          textTransform: "uppercase",
        }}
      >
        French Flow
      </span>
      <div
        style={{
          width: 30,
          height: 2,
          backgroundColor: "rgba(0,0,0,0.1)",
          borderRadius: 1,
        }}
      />
    </div>
  );
};

export const VocabularyGridComposition: React.FC<VocabularyGridProps> = ({
  title,
  words,
  bgMusicSrc,
  timeline = [],
}) => {
  const frame = useCurrentFrame();

  const activeIndex = timeline.findIndex(
    (t) => frame >= t.startFrame && frame < t.startFrame + t.durationInFrames,
  );
  const activeWordIndex =
    activeIndex >= 0 ? timeline[activeIndex].wordIndex : -1;

  const gridStyle: React.CSSProperties = {
    display: "grid",
    gridTemplateColumns: "1fr 1fr 1fr",
    gridTemplateRows: "1fr 1fr",
    gap: 16,
    width: "100%",
    maxWidth: 680,
    padding: "0 20px",
  };

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#f0f2f5",
      }}
    >
      {timeline.map((entry, i) => (
        <Sequence
          key={`audio-${i}`}
          from={entry.startFrame}
          durationInFrames={entry.durationInFrames}
        >
          <Audio src={staticFile(words[entry.wordIndex].audioSrc)} />
        </Sequence>
      ))}

      {bgMusicSrc && (
        <Audio src={staticFile(bgMusicSrc)} volume={0.08} loop />
      )}

      <AbsoluteFill
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "60px 40px",
        }}
      >
        <TitleBar text={title} />

        <div style={gridStyle}>
          {words.map((word, i) => (
            <VocabularyCell
              key={i}
              word={word}
              index={i}
              isActive={i === activeWordIndex}
            />
          ))}
        </div>
      </AbsoluteFill>

      <Branding />
    </AbsoluteFill>
  );
};
