import { execSync } from 'child_process';
try {
  console.log(execSync('python3 -c "import pkg_resources; print([p.project_name for p in pkg_resources.working_set])"').toString());
} catch (e) {
  console.log('Error:', e);
}
