// <marquee> is deprecated-but-still-rendered by every major browser, and
// it's the whole point of the joke here -- React's JSX types just don't
// know about it, so we teach them.
import "react";

declare module "react" {
  namespace JSX {
    interface IntrinsicElements {
      marquee: React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement>;
    }
  }
}
