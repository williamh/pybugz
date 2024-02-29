#compdef bugz
# Copyright 2009 Ingmar Vanhassel <ingmar@exherbo.org>
# vim: set et sw=2 sts=2 ts=2 ft=zsh :

_bugz() {
  local -a _bugz_options _bugz_commands
  local cmd

  _bugz_options=(
    '(-b --base)'{-b,--base}'[bugzilla base URL]:bugzilla url: '
    '(-u --user)'{-u,--user}'[user name (if required)]:user name:_users'
    '(-p --password)'{-p,--password}'[password (if required)]:password: '
    '--columns[number of columns to use when displaying output]:number: '
    '--skip-auth[do not authenticate]'
    '(-q --quiet)'{-q,--quiet}'[do not display status messages]'
  )
  _bugz_commands=(
    'attach:attach file to a bug'
    'attachment:get an attachment from bugzilla'
    'get:get a bug from bugzilla'
    'help:display subcommands'
    'modify:modify a bug (eg. post a comment)'
    'post:post a new bug into bugzilla'
    'search:search for bugs in bugzilla'
  )

  for (( i=1; i <= ${CURRENT}; i++ )); do
    cmd=${_bugz_commands[(r)${words[${i}]}:*]%%:*}
    (( ${#cmd} )) && break
  done

  if (( ${#cmd} )); then
    local curcontext="${curcontext%:*:*}:bugz-${cmd}:"

    while [[ ${words[1]} != ${cmd} ]]; do
      (( CURRENT-- ))
      shift words
    done

    _call_function ret _bugz_cmd_${cmd}
    return ret
  else
    _arguments -s : $_bugz_options
    _describe -t commands 'commands' _bugz_commands
  fi
}

(( ${+functions[_bugz_cmd_attach]} )) ||
_bugz_cmd_attach()
{
  _arguments -s : \
    '(--content_type= -c)'{--content_type=,-c}'[mimetype of the file]:MIME-Type:_mime_types' \
    '(--title= -t)'{--title=,-t}'[a short description of the attachment]:title: ' \
    '(--description= -d)'{--description=,-d}'[a long description of the attachment]:description: ' \
    '(--bigfile)'{--bigfile}'[the attachment is a big file]:bigfile: ' \
    '--help[show help message and exit]'
}

(( ${+functions[_bugz_cmd_attachment]} )) ||
_bugz_cmd_attachment()
{
  _arguments -s : \
    '--help[show help message and exit]' \
    '(--view -v)'{--view,-v}'[print attachment rather than save]'
}


(( ${+functions[_bugz_cmd_get]} )) ||
_bugz_cmd_get()
{
  _arguments -s : \
    '--help[show help message and exit]' \
    '(--no-comments -n)'{--no-comments,-n}'[do not show comments]'
}

(( ${+functions[_bugz_cmd_modify]} )) ||
_bugz_cmd_modify()
{
  _arguments -s : \
    '--add-blocked=[add a bug to the blocked list]:bug: ' \
    '--add-dependson=[add a bug to the depends list]:bug: ' \
    '--add-cc=[add an email to CC list]:email: ' \
    '(--assigned-to= -a)'{--assigned-to=,-a}'[assign bug to someone other than the default assignee]:assignee: ' \
    '(--comment= -c)'{--comment=,-c}'[add comment to bug]:Comment: ' \
    '(--comment-editor -C)'{--comment-editor,-C}'[add comment via default EDITOR]' \
    '(--comment-from= -F)'{--comment-from=,-F}'[add comment from file]:file:_files' \
    '(--duplicate= -d)'{--duplicate=,-d}'[mark bug as a duplicate of bug number]:bug: ' \
    '--fixed[mark bug as RESOLVED, FIXED]' \
    '--help[show help message and exit]' \
    '--invalid[mark bug as RESOLVED, INVALID]' \
    '(--keywords= -k)'{--keywords=,-k}'[list of bugzilla keywords]:keywords: ' \
    '--priority=[set the priority field of the bug]:priority: ' \
    '(--resolution= -r)'{--resolution=,-r}'[set new resolution (only if status = RESOLVED)]' \
    '--remove-cc=[remove an email from the CC list]:email: ' \
    '--remove-dependson=[remove a bug from the depends list]:bug: ' \
    '--remove-blocked=[remove a bug from the blocked list]:bug: ' \
    '(--severity= -S)'{--severity=,-S}'[set severity of the bug]:severity: ' \
    '(--status -s=)'{--status=,-s}'[set new status of bug (eg. RESOLVED)]:status: ' \
    '(--title= -t)'{--title=,-t}'[set title of the bug]:title: ' \
    '(--url= -U)'{--url=,-u}'[set URL field of the bug]:URL: ' \
    '(--whiteboard= -w)'{--whiteboard=,-w}'[set status whiteboard]:status whiteboard: '
}

(( ${+functions[_bugz_cmd_post]} )) ||
_bugz_cmd_post()
{
  _arguments -s : \
    '(--assigned-to= -a)'{--assigned-to=,-a}'[assign bug to someone other than the default assignee]:assignee: ' \
    '--batch[work in batch mode, non-interactively]' \
    '--blocked[add a list of blocker bugs]:blockers: ' \
    '--cc=[add a list of emails to cc list]:email(s): ' \
    '--commenter[email of a commenter]:email: ' \
    '--depends-on[add a list of bug dependencies]:dependencies: ' \
    '(--description= -d)'{--description=,-d}'[description of the bug]:description: ' \
    '(--description-from= -F)'{--description-from=,-f}'[description from contents of a file]:file:_files' \
    '--help[show help message and exit]' \
    '(--keywords= -k)'{--keywords=,-k}'[list of bugzilla keywords]:keywords: ' \
    '(--append-command)--no-append-command[do not append command output]' \
    '(--title= -t)'{--title=,-t}'[title of your bug]:title: ' \
    '(--url= -U)'{--url=,-U}'[URL associated with the bug]:url: ' \
    '--priority[priority of this bug]:priority: ' \
    '--severity[severity of this bug]:severity: '
}

(( ${+functions[_bugz_cmd_search]} )) ||
_bugz_cmd_search()
{
  # TODO --component,--status,--product,--priority can be specified multiple times
  _arguments -s : \
    '(--assigned-to= -a)'{--assigned-to=,-a}'[the email adress the bug is assigned to]:email: ' \
    '--cc=[restrict by CC email address]:email: ' \
    '(--comments -c)'{--comments,-c}'[search comments instead of title]:comment: ' \
    '(--component= -C)'{--component=,-C}'[restrict by component]:component: ' \
    '--help[show help message and exit]' \
    '(--keywords= -k)'{--keywords=,-k}'[bug keywords]:keywords: ' \
    '--severity=[restrict by severity]:severity: ' \
    '--show-status[show bug status]' \
    '(--status= -s)'{--status=,-s}'[bug status]:status: ' \
    '(--order= -o)'{--order=,-o}'[sort by]:order:((number\:"bug number" assignee\:"assignee field" importance\:"importance field" date\:"last changed"))' \
    '--priority=[restrict by priority]:priority: ' \
    '--product=[restrict by product]:product: ' \
    '(--reporter= -r)'{--reporter=,-r}'[email of the reporter]:email: ' \
    '(--whiteboard= -w)'{--whiteboard=,-w}'[status whiteboard]:status whiteboard: '
}

_bugz

