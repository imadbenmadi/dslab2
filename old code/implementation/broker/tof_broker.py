from config import FOG_MIPS, EC_THRESHOLD
from environment.task import DAGTask, DAGStep

class TOFBroker:
    def __init__(self, threshold: float = EC_THRESHOLD, fog_mips: int = FOG_MIPS):
        self.threshold = threshold
        self.fog_mips = fog_mips
        self.stats = {'boulders': 0, 'pebbles': 0, 'total': 0}

    def compute_ec(self, step: DAGStep) -> float:
        """EC = MI / fog_MIPS  (seconds)"""
        return step.MI / self.fog_mips

    def classify(self, step: DAGStep) -> str:
        """Returns 'boulder' or 'pebble'"""
        # Keep threshold boundary as fog-capable so EC==threshold is still treated as pebble.
        return 'boulder' if self.compute_ec(step) > self.threshold else 'pebble'

    def process_dag(self, task: DAGTask) -> dict:
        """
        Classify every offloadable DAG step.
        Returns {'boulders': [steps], 'pebbles': [steps]}
        """
        boulders, pebbles = [], []
        for step in task.steps.values():
            if step.assigned_to == 'device':
                continue                        # Step 1 always runs on device
            ec = self.compute_ec(step)
            step.ec = ec
            if ec > self.threshold:
                step.classification = 'boulder'
                step.assigned_to = 'CLOUD'      # Immediate routing decision
                boulders.append(step)
                self.stats['boulders'] += 1
            else:
                step.classification = 'pebble'
                pebbles.append(step)
                self.stats['pebbles'] += 1
            self.stats['total'] += 1
        return {'boulders': boulders, 'pebbles': pebbles}

    def reset_stats(self):
        self.stats = {'boulders': 0, 'pebbles': 0, 'total': 0}

    @property
    def boulder_rate(self):
        if self.stats['total'] == 0:
            return 0
        return self.stats['boulders'] / self.stats['total']
