;;; beancount.el --- A minor mode that can be used to edit beancount input files.

;; Copyright (C) 2013 Martin Blais <blais@furius.ca>

;; This file is not part of GNU Emacs.

(require 'ido) ;; For completing read.
(require 'font-lock)


(define-minor-mode beancount-mode
  "A minor mode to help editing Beancount files.
This can be used within other text modes, in particular, org-mode
is great for sectioning large files with many transactions."
  :init-value nil
  :lighter " Beancount"
  :keymap
  '(
    ([(control c)(\')] . beancount-insert-account)
    ([(control c)(control g)] . beancount-transaction-set-flag)
    ([(control c)(r)] . beancount-init-accounts)
    ([(control c)(l)] . beancount-check)
    ([(control c)(\;)] . beancount-align-transaction)
    )
  :group 'beancount

  ;; The following is mostly lifted from lisp-mode.
  (make-local-variable 'paragraph-ignore-fill-prefix)
  (setq paragraph-ignore-fill-prefix t)
  (make-local-variable 'fill-paragraph-function)
  (setq fill-paragraph-function 'lisp-fill-paragraph)

  (make-local-variable 'comment-start)
  (setq comment-start ";; ")
  (make-local-variable 'comment-start-skip)

  ;; Look within the line for a ; following an even number of backslashes
  ;; after either a non-backslash or the line beginning.
  (setq comment-start-skip "\\(\\(^\\|[^\\\\\n]\\)\\(\\\\\\\\\\)*\\);+ *")
  (make-local-variable 'font-lock-comment-start-skip)
  ;; Font lock mode uses this only when it KNOWS a comment is starting.
  (setq font-lock-comment-start-skip ";+ *")
  (make-local-variable 'comment-add)
  (setq comment-add 1) ;; Default to `;;' in comment-region

  ;; No tabs by default.
  (set (make-local-variable 'indent-tabs-mode) nil)

  ;; Customize font-lock for beancount.
  ;;
  ;; Important: you have to use 'nil for the mode here because in certain major
  ;; modes (e.g. org-mode) the font-lock-keywords is a buffer-local variable.
  (if beancount-mode
      (font-lock-add-keywords nil beancount-font-lock-defaults)
    (font-lock-remove-keywords nil beancount-font-lock-defaults))
  (font-lock-fontify-buffer)

  (when beancount-mode
    (make-variable-buffer-local 'beancount-accounts)
    (beancount-init-accounts))
  )


(defun beancount-init-accounts ()
  "Initialize or reset the list of accounts."
  (interactive)
  (setq beancount-accounts (beancount-get-accounts))
  (message "Accounts updated."))


(defvar beancount-font-lock-defaults
  `(;; Comments
    (";.+" . font-lock-comment-face)

    ;; Strings
    ("\".*?\"" . font-lock-string-face)

    ;; Reserved keywords
    (,(regexp-opt '("txn" "balance" "open" "close" "pad" "event" "price" "note" "document"
                    "pushtag" "poptag")) . font-lock-keyword-face)

    ;; Tags & Links
    ("[#\\^][A-Za-z0-9\-_/.]+" . font-lock-type-face)

    ;; Date
    ("[0-9][0-9][0-9][0-9][-/][0-9][0-9][-/][0-9][0-9]" . font-lock-constant-face)

    ;; Account
    ("\\([A-Z][A-Za-z0-9\-]+:\\)+\\([A-Z][A-Za-z0-9\-]+\\)" . font-lock-builtin-face)

    ;; Txn Flags
    ("! " . font-lock-warning-face)

    ;; Number + Currency
    ;;; ("\\([\\-+]?[0-9]+\\(\\.[0-9]+\\)?\\)\\s-+\\([A-Z][A-Z0-9'\.]\\{1,10\\}\\)" . )

    ))


(defvar beancount-account-regexp (concat (regexp-opt '("Assets"
                                                       "Liabilities"
                                                       "Equity"
                                                       "Income"
                                                       "Expenses"))
                                         "\\(:[A-Z][A-Za-z0-9-_:]+\\)")
  "A regular expression to match account names.")


(defvar beancount-accounts nil
  "A list of the accounts available in this buffer. This is a
  cache of the value computed by beancount-get-accounts.")


(defun beancount-hash-keys (hashtable)
  "Extract all the keys of the given hashtable. Return a sorted list."
  (let (rlist)
    (maphash (lambda (k v) (push k rlist)) hashtable)
    rlist))


(defun beancount-get-accounts ()
  "Heuristically obtain a list of all the accounts used in all the postings.
We ignore patterns seen the line 'exclude-line'. If ALL is non-nil, look
for account names in postings as well (default is to look at the @defaccount
declarations only."
  (let ((accounts (make-hash-table :test 'equal)))
    (save-excursion
      (goto-char (point-min))
      (while (re-search-forward beancount-account-regexp nil t)
        (puthash (match-string-no-properties 0) nil accounts)))
    (sort (beancount-hash-keys accounts) 'string<)))


(defun beancount-insert-account (account-name)
  "Insert one of the valid account names in this file (using ido
niceness)."
  (interactive
   (list (ido-completing-read "Account: " beancount-accounts nil nil (thing-at-point 'word))))
  (let ((bounds (bounds-of-thing-at-point 'word)))
    (when bounds
      (delete-region (car bounds) (cdr bounds))))
  (insert account-name))


(defun beancount-transaction-set-flag ()
  (interactive)
  (save-excursion
    (backward-paragraph 1)
    (forward-line 1)
    (replace-string "!" "*" nil (line-beginning-position) (line-end-position))))


(defmacro beancount-for-line-in-region (begin end &rest exprs)
  "Iterate over each line in region until an empty line is encountered."
  `(save-excursion
     (let ((end-marker (set-marker (make-marker) ,end)))
       (goto-char ,begin)
       (forward-line 1)
       (beginning-of-line)
       (while (< (point) end-marker)
         (progn ,@exprs)
         (forward-line 1)
         (beginning-of-line)
         ))))

(defun beancount-align-postings (begin end &optional currency-column)
  "Align all postings in the given region. CURRENCY-COLUMN is the character
at which to align the beginning of the amount's currency."
  (interactive "r")
  (beancount-for-line-in-region
   begin end
   (let* ((line (thing-at-point 'line))
          (number-width 12)
          (number-format (format "%%%ss %%s" number-width))
          (account-format (format "  %%-%ss" (- currency-column 2 number-width 1))))
     (when (string-match
            (concat "^[ \t]+"
                    "\\(?:\\(.\\)[ \t]+\\)?"
                    "\\([A-Z][A-Za-z0-9_-]+:[A-Za-z0-9_:\\-]+\\)"
                    "[ \t]+"
                    "\\(?:\\([-+]?[0-9.]+\\)[ \t]+\\(.*\\)\\)")
            line)
       (delete-region (line-beginning-position) (line-end-position))
       (let* ((flag (match-string 1 line))
              (account (match-string 2 line))
              (flag-account
               (if flag
                   (format "%s %s" flag account)
                 (format "%s" account)))
              (number (match-string 3 line))
              (rest (match-string 4 line)) )
         (insert (format account-format flag-account))
         (when (and number rest)
           (insert (format number-format number rest))))))))

(defun beancount-align-transaction ()
  "Align postings under the point's paragraph."
  (interactive)
  (let ((begin (save-excursion
                 (forward-paragraph -1)
                 (point)))
        (end (save-excursion
               (forward-paragraph 1)
               (point)))
        (beancount-align-currency-column fill-column))
    (beancount-align-postings begin end beancount-align-currency-column)))


(defvar beancount-check-program "bean-check"
  "Program to run to run just the parser and validator on an
  input file.")

(defun beancount-check ()
  (interactive)
  (let ((compilation-read-command nil)
        (compile-command
         (format "%s %s" beancount-check-program (buffer-file-name))))
    (call-interactively 'compile)))


(provide 'beancount)
