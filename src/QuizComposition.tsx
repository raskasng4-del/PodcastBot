import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  useVideoConfig,
  Easing,
  Sequence,
  Img,
  Audio,
  staticFile,
} from "remotion";

const colors = {
  bg: "#1a1a2e",
  accent: "#e94560",
  text: "#ffffff",
  muted: "#cccccc",
};

const FlagBar: React.FC<{ color: string; width: number }> = ({
  color,
  width,
}) => (
  <div
    style={{
      width: `${width}%`,
      height: "100%",
      backgroundColor: color,
    }}
  />
);

const FrenchFlagBackground: React.FC<{ opacity: number }> = ({ opacity }) => (
  <AbsoluteFill
    style={{
      display: "flex",
      flexDirection: "row",
      opacity,
    }}
  >
    <FlagBar color="#002395" width={33.33} />
    <FlagBar color="#FFFFFF" width={33.33} />
    <FlagBar color="#ED2939" width={33.33} />
  </AbsoluteFill>
);

const QuestionText: React.FC<{ text: string; questionDur: number }> = ({
  text,
  questionDur,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const opacity = interpolate(frame, [0, fps * 0.5], [0, 1], {
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  const scale = interpolate(frame, [0, fps * 0.5], [0.7, 1], {
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  const y = interpolate(frame, [0, fps * 0.5], [30, 0], {
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  const exitOpacity = interpolate(
    frame,
    [(questionDur - 0.5) * fps, questionDur * fps],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  return (
    <div
      style={{
        fontFamily: "Arial, Helvetica, sans-serif",
        fontSize: 72,
        fontWeight: 700,
        color: "#ffffff",
        opacity: Math.min(opacity, exitOpacity),
        transform: `scale(${scale}) translateY(${y}px)`,
        textAlign: "center",
        textShadow: "0 4px 20px rgba(0,0,0,0.6)",
        zIndex: 10,
      }}
    >
      {text}
    </div>
  );
};

const PauseOverlay: React.FC<{ text: string; pauseDur: number }> = ({
  text,
  pauseDur,
}) => {
  const { fps } = useVideoConfig();
  const frame = useCurrentFrame();

  const dots = ["", ".", "..", "..."];
  const dotIndex = Math.floor(frame / (fps * 0.3)) % dots.length;

  const opacity = interpolate(
    frame,
    [0, fps * 0.3, (pauseDur - 0.3) * fps, pauseDur * fps],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  return (
    <div
      style={{
        fontFamily: "Arial, Helvetica, sans-serif",
        fontSize: 36,
        fontWeight: 300,
        color: colors.muted,
        opacity,
        textAlign: "center",
        position: "absolute",
        bottom: "15%",
        zIndex: 10,
      }}
    >
      {text}{dots[dotIndex]}
    </div>
  );
};

const ObjectImage: React.FC<{ src: string }> = ({ src }) => {
  const { fps } = useVideoConfig();
  const frame = useCurrentFrame();

  const fadeIn = interpolate(
    frame,
    [0, fps * 0.5],
    [0, 1],
    { extrapolateRight: "clamp", easing: Easing.bezier(0.16, 1, 0.3, 1) },
  );

  const breathe = Math.sin((frame / fps) * Math.PI * 0.5) * 3;
  const scale = 1 + breathe / 100;

  return (
    <Img
      src={src}
      style={{
        maxWidth: "60%",
        maxHeight: "50%",
        borderRadius: 20,
        boxShadow: "0 8px 40px rgba(0,0,0,0.5)",
        opacity: fadeIn,
        transform: `scale(${scale})`,
        objectFit: "contain",
      }}
    />
  );
};

const AnswerReveal: React.FC<{
  name: string;
  article: string;
  prefix: string;
}> = ({ name, article, prefix }) => {
  const { fps } = useVideoConfig();
  const frame = useCurrentFrame();

  const textOpacity = interpolate(
    frame,
    [0, fps * 0.4],
    [0, 1],
    { extrapolateRight: "clamp", easing: Easing.bezier(0.16, 1, 0.3, 1) },
  );

  const textY = interpolate(
    frame,
    [0, fps * 0.4],
    [30, 0],
    { extrapolateRight: "clamp", easing: Easing.bezier(0.16, 1, 0.3, 1) },
  );

  const underlineWidth = interpolate(
    frame,
    [fps * 0.2, fps * 0.6],
    [0, 100],
    { extrapolateRight: "clamp" },
  );

  return (
    <div
      style={{
        textAlign: "center",
        opacity: textOpacity,
        transform: `translateY(${textY}px)`,
        marginTop: 30,
      }}
    >
      <div
        style={{
          fontFamily: "Arial, Helvetica, sans-serif",
          fontSize: 60,
          fontWeight: 400,
          color: "#ffffff",
          textShadow: "0 4px 20px rgba(0,0,0,0.6)",
        }}
      >
        {prefix}{" "}
        <span
          style={{
            color: colors.accent,
            fontWeight: 700,
            fontSize: 68,
          }}
        >
          {article} {name}
        </span>
      </div>
      <div
        style={{
          width: `${underlineWidth}%`,
          height: 4,
          backgroundColor: colors.accent,
          marginTop: 10,
          marginLeft: "auto",
          marginRight: "auto",
          borderRadius: 2,
          maxWidth: 400,
        }}
      />
    </div>
  );
};

export interface QuizProps {
  imageUrl: string;
  objectName: string;
  objectArticle: string;
  questionAudio: string;
  answerAudio: string;
  questionText?: string;
  pauseText?: string;
  answerPrefix?: string;
  questionDuration?: number;
  pauseDuration?: number;
  answerDuration?: number;
}

export const QuizComposition: React.FC<QuizProps> = ({
  imageUrl,
  objectName,
  objectArticle,
  questionAudio,
  answerAudio,
  questionText = "Qu'est-ce que c'est ?",
  pauseText = "Réfléchissez",
  answerPrefix = "C'est",
  questionDuration = 2.5,
  pauseDuration = 3,
  answerDuration = 3,
}) => {
  const { fps } = useVideoConfig();
  const frame = useCurrentFrame();

  const qFrames = Math.round(questionDuration * fps);
  const pFrames = Math.round(pauseDuration * fps);
  const aFrames = Math.round(answerDuration * fps);

  const bgOpacity = interpolate(frame, [0, fps * 0.3], [0, 1], {
    extrapolateRight: "clamp",
  });

  const scene2FadeIn = interpolate(
    frame,
    [qFrames - fps * 0.2, qFrames + fps * 0.3],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const scene2FadeOut = interpolate(
    frame,
    [qFrames + pFrames - fps * 0.5, qFrames + pFrames + fps * 0.2],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const scene2Opacity = Math.min(scene2FadeIn, scene2FadeOut);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: colors.bg,
        justifyContent: "center",
        alignItems: "center",
        opacity: bgOpacity,
      }}
    >
      <Sequence from={0} durationInFrames={qFrames}>
        <AbsoluteFill
          style={{
            justifyContent: "center",
            alignItems: "center",
            overflow: "hidden",
          }}
        >
          <FrenchFlagBackground opacity={0.15} />
          <QuestionText text={questionText} questionDur={questionDuration} />
        </AbsoluteFill>
        <Audio src={staticFile(questionAudio)} />
      </Sequence>

      <Sequence from={qFrames} durationInFrames={pFrames}>
        <AbsoluteFill
          style={{
            justifyContent: "center",
            alignItems: "center",
            opacity: scene2Opacity,
          }}
        >
          <ObjectImage src={imageUrl} />
          <PauseOverlay text={pauseText} pauseDur={pauseDuration} />
        </AbsoluteFill>
      </Sequence>

      <Sequence from={qFrames + pFrames} durationInFrames={aFrames}>
        <AbsoluteFill
          style={{
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <ObjectImage src={imageUrl} />
            <AnswerReveal
              name={objectName}
              article={objectArticle}
              prefix={answerPrefix}
            />
          </div>
        </AbsoluteFill>
        <Audio src={staticFile(answerAudio)} />
      </Sequence>
    </AbsoluteFill>
  );
};
