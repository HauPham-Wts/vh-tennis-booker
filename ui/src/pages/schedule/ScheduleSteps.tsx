import { useOverview } from "../../api/queries";
import { QueryView } from "../../components/QueryView";
import { DryRunStep } from "./DryRunStep";
import { ScheduleStep } from "./ScheduleStep";

/** The dry run, then the daily switch: the Schedule screen, also the last welcome step. */
export function ScheduleSteps() {
  const overview = useOverview();
  return (
    <QueryView query={overview}>
      {({ running, schedule }) => (
        <>
          <DryRunStep running={running} wake={schedule.wake_at} start={schedule.start_at} />
          <ScheduleStep />
        </>
      )}
    </QueryView>
  );
}
