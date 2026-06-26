### **GitHub Workflows**

#### 📌 **Overview**

This directory (`.github/workflows/`) contains GitHub Actions workflow definitions that automate various tasks such as
CI/CD, releases, and repository synchronization.

#### ⚙️ **Workflows**

Below is a list of the workflows included in this repository:

| Workflow File             | Purpose                                                              |
|---------------------------|----------------------------------------------------------------------|
| `app_backend-test.yml`    | Build the React assets, then run app_backend lint and tests.          |
| `app_frontend-vitest.yml` | Run React lint, Vitest, Knip, and coverage reporting.                 |
| `core-python.yml`         | Run core package lint and tests across supported Python versions.     |
| `dockerfile-lint.yml`     | Run Hadolint to check Dockerfiles for best practices.                 |
| `frontend-test.yml`       | Run legacy frontend Python checks.                                    |
| `infra-python.yml`        | Run infra package lint checks across supported Python versions.       |
| `pulumi-up.yml`           | Run Pulumi `up --refresh` after merges to `main` or `dev`.            |
| `shellcheck.yml`          | Run [shellcheck](https://github.com/koalaman/shellcheck/).            |
| `yaml-format.yml`         | Run YAML linter tool (yamlfmt).                                       |

`pulumi-up.yml` is a repository-specific CD workflow restored on top of the
upstream split CI workflow layout. It deploys from the `infra/` Pulumi project
and expects the DataRobot, Pulumi, and OpenAI credentials to be configured as
GitHub environment secrets.

---

Feel free to update this document as new workflows are added or modified! ✨
