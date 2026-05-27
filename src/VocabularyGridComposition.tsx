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

const YELLOW = "#FFD700";
const WHITE = "#FFFFFF";
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
        color: YELLOW,
        textAlign: "center",
        opacity,
        transform: `translateY(${y}px)`,
        marginBottom: 32,
        letterSpacing: 1,
        textShadow: "0 0 30px rgba(255, 215, 0, 0.15)",
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
        backgroundColor: "#1A1A1A",
        boxShadow: isActive
          ? "0 8px 30px rgba(0, 212, 255, 0.3)"
          : "0 4px 24px rgba(0,0,0,0.5)",
        border: isActive
          ? `2px solid ${ACTIVE_BORDER}`
          : "2px solid rgba(255,255,255,0.06)",
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
          color: YELLOW,
          textAlign: "center",
          textShadow: "0 0 20px rgba(255, 215, 0, 0.2)",
        }}
      >
        {word.french}
      </span>
      <span
        style={{
          fontFamily: "Arial, Helvetica, sans-serif",
          fontSize: 16,
          fontWeight: 400,
          color: WHITE,
          textAlign: "center",
          opacity: 0.7,
        }}
      >
        {word.english}
      </span>
    </div>
  );
};

const SubscribeButton: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const fadeIn = interpolate(frame, [fps * 2, fps * 3], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  const breathe = Math.sin((frame / fps) * Math.PI * 1.2) * 0.04 + 1;

  return (
    <div
      style={{
        position: "absolute",
        bottom: 90,
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        opacity: fadeIn,
        transform: `scale(${breathe})`,
      }}
    >
      <div
        style={{
          fontFamily: "Arial, Helvetica, sans-serif",
          fontSize: 22,
          fontWeight: 700,
          color: WHITE,
          backgroundColor: "#FF0000",
          padding: "14px 48px",
          borderRadius: 50,
          letterSpacing: 1,
          textTransform: "uppercase",
          boxShadow: "0 4px 30px rgba(255, 0, 0, 0.4)",
        }}
      >
        Subscribe
      </div>
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
          color: "rgba(255,255,255,0.3)",
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
          backgroundColor: "rgba(255,255,255,0.15)",
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
        backgroundColor: "#000000",
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

      <SubscribeButton />
      <Branding />
    </AbsoluteFill>
  );
};
