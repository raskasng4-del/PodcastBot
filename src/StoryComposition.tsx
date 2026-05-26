import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Easing,
  Audio,
  staticFile,
  spring,
  Sequence,
} from "remotion";
import { useMemo } from "react";

const BG = "#0d0d1a";
const ACCENT = "#e94560";
const FONT_SIZE = 40;
const LINE_HEIGHT = FONT_SIZE + 16;
const MARGIN_TOP = 180;
const MARGIN_BOTTOM = 180;
const VISIBLE_HEIGHT = 1920 - MARGIN_TOP - MARGIN_BOTTOM;
const LINES_VISIBLE = Math.floor(VISIBLE_HEIGHT / LINE_HEIGHT);
const FADE_ZONE = LINES_VISIBLE * 0.25;

const TITLE_HOLD_FRAMES = 90;
const END_HOLD_FRAMES = 60;

export interface StoryLine {
  text: string;
  isHeading?: boolean;
}

export interface StoryProps {
  title: string;
  lines: StoryLine[];
  audioSrc: string;
  bgMusicSrc?: string;
}

const GradientOverlay: React.FC = () => (
  <>
    <AbsoluteFill
      style={{
        height: MARGIN_TOP + FADE_ZONE * LINE_HEIGHT,
        top: 0,
        background: `linear-gradient(180deg, ${BG} 0%, ${BG} ${
          MARGIN_TOP / (MARGIN_TOP + FADE_ZONE * LINE_HEIGHT) * 100
        }%, transparent 100%)`,
        zIndex: 10,
        pointerEvents: "none",
      }}
    />
    <AbsoluteFill
      style={{
        height: MARGIN_BOTTOM + FADE_ZONE * LINE_HEIGHT,
        bottom: 0,
        background: `linear-gradient(0deg, ${BG} 0%, ${BG} ${
          MARGIN_BOTTOM / (MARGIN_BOTTOM + FADE_ZONE * LINE_HEIGHT) * 100
        }%, transparent 100%)`,
        zIndex: 10,
        pointerEvents: "none",
      }}
    />
  </>
);

const TitleScene: React.FC<{
  title: string;
  frame: number;
  fps: number;
}> = ({ title, frame, fps }) => {
  const titleIn = spring({
    frame,
    fps,
    config: { damping: 12, stiffness: 80 },
  });

  const titleOut = interpolate(
    frame,
    [TITLE_HOLD_FRAMES - 30, TITLE_HOLD_FRAMES],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const opacity = Math.min(titleIn, titleOut);
  const y = interpolate(titleIn, [0, 1], [60, 0]);

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        opacity,
      }}
    >
      <div
        style={{
          fontFamily: "Arial, Helvetica, sans-serif",
          fontSize: FONT_SIZE * 1.8,
          fontWeight: 700,
          color: ACCENT,
          textAlign: "center",
          textShadow: "0 4px 24px rgba(233,69,96,0.3)",
          transform: `translateY(${y}px)`,
          padding: "0 60px",
        }}
      >
        {title}
      </div>
    </AbsoluteFill>
  );
};

const LineItem: React.FC<{
  text: string;
  isHeading: boolean;
  index: number;
  totalLines: number;
  scrollProgress: number;
}> = ({ text, isHeading, index, totalLines, scrollProgress }) => {
  const lineCenter = (index + 0.5) / totalLines;
  const distFromCenter = scrollProgress - lineCenter;
  const screenPos = distFromCenter * totalLines;

  const absScreenPos = Math.abs(screenPos);
  const rawOpacity = interpolate(
    absScreenPos,
    [0, LINES_VISIBLE * 0.35, LINES_VISIBLE * 0.55],
    [1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const opacity = interpolate(rawOpacity, [0, 1], [0, 1], {
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  const y = interpolate(
    screenPos,
    [-LINES_VISIBLE / 2, LINES_VISIBLE / 2],
    [-VISIBLE_HEIGHT / 2 + LINE_HEIGHT / 2, VISIBLE_HEIGHT / 2 - LINE_HEIGHT / 2],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const baseY = 1920 / 2;
  const scale = interpolate(absScreenPos, [0, LINES_VISIBLE * 0.3], [1, 0.92], {
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        left: 80,
        right: 80,
        top: baseY + y - LINE_HEIGHT / 2,
        height: LINE_HEIGHT,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        opacity,
        transform: `scale(${scale})`,
      }}
    >
      <span
        style={{
          fontFamily: "Arial, Helvetica, sans-serif",
          fontSize: isHeading ? FONT_SIZE * 1.4 : FONT_SIZE,
          fontWeight: isHeading ? 700 : 400,
          color: isHeading ? ACCENT : "#ffffff",
          textAlign: "center",
          textShadow: "0 2px 12px rgba(0,0,0,0.5)",
          lineHeight: `${LINE_HEIGHT}px`,
        }}
      >
        {text}
      </span>
    </div>
  );
};

export const StoryComposition: React.FC<StoryProps> = ({
  title,
  lines,
  audioSrc,
  bgMusicSrc,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames, fps } = useVideoConfig();

  const allLines = useMemo(() => {
    const result: StoryLine[] = [];
    if (title) {
      result.push({ text: title, isHeading: true });
      result.push({ text: "", isHeading: false });
    }
    for (const line of lines) {
      result.push(line);
      result.push({ text: "", isHeading: false });
    }
    if (result.length < 10) {
      const extra = 10 - result.length;
      for (let i = 0; i < extra; i++)
        result.push({ text: "", isHeading: false });
    }
    return result;
  }, [title, lines]);

  const scrollDuration = durationInFrames - TITLE_HOLD_FRAMES - END_HOLD_FRAMES;
  const scrollFrame = Math.max(0, frame - TITLE_HOLD_FRAMES);

  const rawScroll = scrollDuration > 0
    ? interpolate(
        scrollFrame,
        [0, scrollDuration],
        [0, 1],
        {
          easing: Easing.bezier(0.0, 0.0, 1.0, 1.0),
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        },
      )
    : 0;

  const easedScroll = interpolate(rawScroll, [0, 1], [0, 1], {
    easing: Easing.bezier(0.1, 0.0, 0.3, 1.0),
  });

  const scrollProgress = interpolate(
    easedScroll,
    [0, 1],
    [-0.05, 1.05],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const bgOpacity = interpolate(frame, [0, 30], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: BG,
        opacity: bgOpacity,
        overflow: "hidden",
      }}
    >
      <Audio src={staticFile(audioSrc)} />

      {bgMusicSrc && (
        <Audio src={staticFile(bgMusicSrc)} volume={0.08} loop />
      )}

      <GradientOverlay />

      <Sequence from={0} durationInFrames={TITLE_HOLD_FRAMES}>
        <TitleScene title={title} frame={frame} fps={fps} />
      </Sequence>

      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        {allLines.map((line, i) => (
          <LineItem
            key={i}
            text={line.text}
            isHeading={line.isHeading || false}
            index={i}
            totalLines={allLines.length}
            scrollProgress={scrollProgress}
          />
        ))}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
