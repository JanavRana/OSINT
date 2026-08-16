import { fmtDate } from "@/lib/format";
import type { TimelineEvent } from "@/types/domain";

export function TimelineFeedItem({ event }: { event: TimelineEvent }) {
  return (
    <div className="flex gap-2 text-xs font-mono">
      <div className="mt-1.5 h-1.5 w-1.5 rounded-full bg-primary shrink-0" aria-hidden="true" />
      <div className="min-w-0">
        <div className="text-foreground">
          <span className="font-bold text-foreground font-sans">{event.actor}</span>{" "}
          <span className="text-muted-foreground uppercase text-[10px]">{event.action}</span>{" "}
          <span className="font-bold text-primary">{event.target}</span>
        </div>
        <div className="text-[10px] text-muted-foreground">
          <time dateTime={event.time}>{fmtDate(event.time)}</time>
        </div>
      </div>
    </div>
  );
}

