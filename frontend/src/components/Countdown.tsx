import { useEffect, useState } from "react";

interface Props {
  unlockAt: string;
  onUnlock: () => void;
}

function getRemaining(unlockAt: string): number {
  return Math.max(0, new Date(unlockAt).getTime() - Date.now());
}

export default function Countdown({ unlockAt, onUnlock }: Props) {
  const [msLeft, setMsLeft] = useState(() => getRemaining(unlockAt));
  const [fired, setFired] = useState(false);

  useEffect(() => {
    if (msLeft <= 0 && !fired) {
      setFired(true);
      onUnlock();
      return;
    }
    const id = setInterval(() => {
      const rem = getRemaining(unlockAt);
      setMsLeft(rem);
      if (rem <= 0) {
        clearInterval(id);
        if (!fired) {
          setFired(true);
          onUnlock();
        }
      }
    }, 1000);
    return () => clearInterval(id);
  }, [unlockAt, onUnlock, fired, msLeft]);

  const totalSec = Math.floor(msLeft / 1000);
  const days = Math.floor(totalSec / 86400);
  const hours = Math.floor((totalSec % 86400) / 3600);
  const minutes = Math.floor((totalSec % 3600) / 60);
  const seconds = totalSec % 60;

  if (msLeft <= 0) return <span>Unlocking...</span>;

  return (
    <span>
      {days}d {hours}h {minutes}m {seconds}s
    </span>
  );
}
