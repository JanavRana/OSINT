import { fmtDate } from "@/lib/format";
import type { TimelineEvent } from "@/types/domain";

export function TimelineFeedItem({ event }: { event: TimelineEvent }) {
  return (
    <div className="flex gap-3 text-xs">
      <div className="mt-1 h-1.5 w-1.5 rounded-full bg-primary shrink-0" aria-hidden="true" />
      <div className="min-w-0">
        <div className="text-foreground">
          <span className="font-medium text-primary">{event.actor}</span>{" "}
          <span className="text-muted-foreground">{event.action.toLowerCase()}</span>{" "}
          <span className="font-mono">{event.target}</span>
        </div>
        <div className="text-[10px] text-muted-foreground">
          <time dateTime={event.time}>{fmtDate(event.time)}</time>
        </div>
      </div>
    </div>
  );
}
