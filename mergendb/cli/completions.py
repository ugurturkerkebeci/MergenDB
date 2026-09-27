"""
Shell completion generator for MergenDB CLI (Bash, Zsh, PowerShell, Fish).
Zero external dependencies.
"""

BASH_COMPLETION = """# MergenDB Bash Completion
_mergen_completions() {
    local cur prev words cword
    _init_completion || return

    local commands="serve test benchmark query export import completions --help --version"
    local formats="csv json jsonl sql"

    if [ "$cword" -eq 1 ]; then
        COMPREPLY=( $(compgen -W "$commands" -- "$cur") )
        return 0
    fi

    case "${words[1]}" in
        serve|server)
            return 0
            ;;
        export)
            if [ "$cword" -eq 2 ]; then
                local tables=$(compgen -f -X '!*.mgdb' -- "$cur")
                COMPREPLY=( $(compgen -W "$tables" -- "$cur") )
            elif [ "$cword" -eq 3 ]; then
                COMPREPLY=( $(compgen -W "$formats" -- "$cur") )
            fi
            ;;
        import)
            if [ "$cword" -eq 2 ]; then
                local tables=$(compgen -f -X '!*.mgdb' -- "$cur")
                COMPREPLY=( $(compgen -W "$tables" -- "$cur") )
            elif [ "$cword" -eq 3 ]; then
                COMPREPLY=( $(compgen -W "$formats" -- "$cur") )
            elif [ "$cword" -eq 4 ]; then
                _filedir
            fi
            ;;
        completions)
            COMPREPLY=( $(compgen -W "bash zsh powershell fish" -- "$cur") )
            ;;
        *)
            _filedir
            ;;
    esac
}
complete -F _mergen_completions mergen
"""

ZSH_COMPLETION = """#compdef mergen
# MergenDB Zsh Completion

_mergen() {
    local curcontext="$curcontext" state line
    typeset -A opt_args

    _arguments -C \
        '1: :->command' \
        '*:: :->args'

    case $state in
        command)
            local -a commands
            commands=(
                'serve:Start MergenDB REST & Studio Web server'
                'test:Run hardware diagnostics & engine test suite'
                'benchmark:Benchmark device throughput and scan speeds'
                'query:Execute a one-off SQL/MergenQL query'
                'export:Export a .mgdb table to CSV, JSON, JSONL, or SQL'
                'import:Import external data into a .mgdb table'
                'completions:Generate shell completion script'
            )
            _describe -t commands 'mergen command' commands
            ;;
        args)
            case $line[1] in
                serve)
                    _message 'port number (default: 8765)'
                    ;;
                completions)
                    _values 'shell' bash zsh powershell fish
                    ;;
                export)
                    _files -g '*.mgdb'
                    ;;
                *)
                    _files
                    ;;
            esac
            ;;
    esac
}

_mergen "$@"
"""

POWERSHELL_COMPLETION = """# MergenDB PowerShell Completion
Register-ArgumentCompleter -Native -CommandName mergen -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)

    $commands = @('serve', 'test', 'benchmark', 'query', 'export', 'import', 'completions', '--help', '--version')
    $shells = @('powershell', 'bash', 'zsh', 'fish')
    $formats = @('csv', 'json', 'jsonl', 'sql')

    $elements = $commandAst.CommandElements
    if ($elements.Count -le 2) {
        $commands | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
            [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
        }
        return
    }

    $subcommand = $elements[1].Extent.Text
    if ($subcommand -eq 'completions') {
        $shells | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
            [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
        }
    }
    elseif ($subcommand -eq 'export' -or $subcommand -eq 'import') {
        if ($elements.Count -eq 3) {
            Get-ChildItem -Filter *.mgdb | ForEach-Object {
                [System.Management.Automation.CompletionResult]::new($_.Name, $_.Name, 'ParameterValue', $_.Name)
            }
        }
        elseif ($elements.Count -eq 4) {
            $formats | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
            }
        }
    }
}
"""

FISH_COMPLETION = """# MergenDB Fish Completion
complete -c mergen -f
complete -c mergen -n "__fish_use_subcommand" -a "serve" -d "Start MergenDB REST & Studio Web server"
complete -c mergen -n "__fish_use_subcommand" -a "test" -d "Run hardware diagnostics & engine test suite"
complete -c mergen -n "__fish_use_subcommand" -a "benchmark" -d "Benchmark device throughput and scan speeds"
complete -c mergen -n "__fish_use_subcommand" -a "query" -d "Execute a one-off SQL/MergenQL query"
complete -c mergen -n "__fish_use_subcommand" -a "export" -d "Export a .mgdb table"
complete -c mergen -n "__fish_use_subcommand" -a "import" -d "Import external data into .mgdb table"
complete -c mergen -n "__fish_use_subcommand" -a "completions" -d "Generate shell completion script"

complete -c mergen -n "__fish_seen_subcommand_from completions" -a "bash zsh powershell fish"
complete -c mergen -n "__fish_seen_subcommand_from export import" -a "csv json jsonl sql"
"""

def generate_completions(shell: str) -> str:
    shell = shell.lower().strip()
    if shell in ("bash", "sh"):
        return BASH_COMPLETION
    elif shell in ("zsh",):
        return ZSH_COMPLETION
    elif shell in ("powershell", "ps", "pwsh"):
        return POWERSHELL_COMPLETION
    elif shell in ("fish",):
        return FISH_COMPLETION
    else:
        raise ValueError(f"Unsupported shell '{shell}'. Supported shells: bash, zsh, powershell, fish.")
