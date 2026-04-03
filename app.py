#!/usr/bin/env python
import os
import re
import sys
from pathlib import Path
from shutil import which
from subprocess import DEVNULL, PIPE, CompletedProcess, run
from typing import Optional

from tadashi import TrEnum
from tadashi.apps import App
from tadashi.translators import Translator

ml4tadashi = os.path.dirname(__file__)
ml4tadashi = os.path.dirname(ml4tadashi)
ml4tadashi = os.path.dirname(ml4tadashi)
ml4tadashi = os.path.dirname(ml4tadashi)
sys.path.append(ml4tadashi)
ml4tadashi = os.path.join(ml4tadashi, "ML4TADASHI")
sys.path.append(ml4tadashi)

import ML4TADASHI

BASE_PATH = Path(__file__).parent / "ref"


class miniAMR(App):
    base: Path

    def __init__(
        self,
        num_ranks: int,
        run_args: Optional[list[str]] = None,
        base: Path = BASE_PATH,
        *,
        source: Path = BASE_PATH / "stencil.c",
        translator: Optional[Translator] = None,
        compiler_options: list = None,
        ephemeral: bool = False,
        populate_scops: bool = True,
    ):
        self.base = base
        self.num_ranks = num_ranks
        if not run_args:
            run_args = []
        self.run_args = run_args
        super().__init__(
            source=source,
            translator=translator,
            compiler_options=compiler_options,
            ephemeral=ephemeral,
            populate_scops=populate_scops,
        )

    @staticmethod
    def _mpich_includes():
        compiler = "mpicc"
        if not which(compiler):
            return []
        cmd = [compiler, "-compile_info"]
        result = run(cmd, stdout=PIPE, stderr=DEVNULL, check=False)
        if result.returncode == 1:
            return []
        stdout = result.stdout.decode()
        opts = stdout.split()
        include_paths = [inc for inc in opts if inc.startswith("-I")]
        return include_paths

    @staticmethod
    def _gcc_includes(compiler):
        if not which(compiler):
            return []
        cmd = [compiler, "-xc", "-E", "-v", "/dev/null"]
        result = run(cmd, stdout=DEVNULL, stderr=PIPE, check=False)
        if result.returncode == 1:
            return []
        stderr = result.stderr.decode()
        include_paths = []
        collect = False
        for line in stderr.split("\n"):
            if collect:
                if not line.startswith(" "):
                    break
                include_paths.append(line[1:])
            if line.startswith("#include <"):
                collect = True
        return include_paths

    @staticmethod
    def _mpifcc_includes():
        compiler = "mpifcc"
        cmd = [compiler, "--print-file-name=include"]
        if not which(compiler):
            return []
        result = run(cmd, stdout=PIPE, stderr=DEVNULL, check=False)
        if result.returncode == 1:
            return []
        stdout = result.stdout.decode()
        includes = [f"-I{inc}/mpi/fujitsu" for inc in stdout.split()]
        return includes

    def codegen_init_args(self):
        return {
            "num_ranks": self.num_ranks,
            "base": self.base,
            "run_args": self.run_args,
        }

    def app_required_options(self) -> list[str]:
        return (
            self._mpich_includes()
            + self._gcc_includes("gcc")
            + self._gcc_includes("mpicc")
            + self._mpifcc_includes()
        )

    def compile_cmd(self, suffix: str) -> list[str]:
        cmd = [
            "make",
            "-j",
            f"-C{self.source.parent}",
            f"STENCIL={self.source.with_suffix('').name}",
            f"EXEC={self.output_binary.name}",
        ]
        mpifcc = "mpifcc"
        if which(mpifcc):
            cmd += [f"CC={mpifcc}", f"LD={mpifcc}"]
        return cmd

    def run_cmd(self) -> list[str]:
        cmd = [
            # "mpirun",
            # "-N",
            # str(self.num_ranks),
            str(self.output_binary),
            "--stencil",
            "0",
            *self.run_args,
        ]
        return cmd

    def extract_runtime(self, proc: CompletedProcess) -> float:
        stdout = proc.stdout.decode()
        lines = stdout.split("\n")
        # scop_idx_check = set([])
        for line in lines:
            # if line.startswith("@@@") and scop_idx_check != line:
            #     scop_idx_check.add(line)
            if line.startswith("Summary:"):
                match = re.match(r".*time (\d+.\d+).*", line)
                # print(f"{scop_idx_check=}")
                return float(match.groups()[0])
        raise Exception("No output found")


def main():
    npz, npx = 1, 1
    kwargs = {
        "num_ranks": npz * npx,
        "run_args": ["--nx", "10", "--ny", "10", "--nz", "82"]
        + ["--npz", str(npz), "--npx", str(npx)],
        "translator": "Pet",
    }
    ML4TADASHI.run(miniAMR, kwargs)


if __name__ == "__main__":
    main()
