import { execSync } from 'child_process';
try {
  console.log('Running pip...');
  console.log(execSync('python3 -m pip install numpy torch deap').toString());
} catch (e) {
  console.log('Error:', e.message);
  console.log('Stdout:', e.stdout?.toString());
  console.log('Stderr:', e.stderr?.toString());
}
