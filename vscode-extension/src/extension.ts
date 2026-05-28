/**
 * Ollama Agent VS Code Extension
 * Main extension entry point
 */

import * as vscode from 'vscode';

export function activate(context: vscode.ExtensionContext) {
    console.log('Ollama Agent extension is now active!');

    // Register commands
    const openChatCommand = vscode.commands.registerCommand('ollamaAgent.openChat', () => {
        vscode.window.showInformationMessage('Opening Ollama Agent Chat...');
        // TODO: Implement chat panel
    });

    const explainCodeCommand = vscode.commands.registerCommand('ollamaAgent.explainCode', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage('No active editor');
            return;
        }

        const selection = editor.document.getText(editor.selection);
        if (!selection) {
            vscode.window.showErrorMessage('No code selected');
            return;
        }

        vscode.window.showInformationMessage('Explaining code...');
        // TODO: Call Ollama API to explain code
    });

    const refactorCodeCommand = vscode.commands.registerCommand('ollamaAgent.refactorCode', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage('No active editor');
            return;
        }

        const selection = editor.document.getText(editor.selection);
        if (!selection) {
            vscode.window.showErrorMessage('No code selected');
            return;
        }

        vscode.window.showInformationMessage('Refactoring code...');
        // TODO: Call Ollama API to refactor code
    });

    const generateTestsCommand = vscode.commands.registerCommand('ollamaAgent.generateTests', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage('No active editor');
            return;
        }

        vscode.window.showInformationMessage('Generating tests...');
        // TODO: Call Ollama API to generate tests
    });

    const generateDocsCommand = vscode.commands.registerCommand('ollamaAgent.generateDocs', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage('No active editor');
            return;
        }

        vscode.window.showInformationMessage('Generating documentation...');
        // TODO: Call Ollama API to generate docs
    });

    const findBugsCommand = vscode.commands.registerCommand('ollamaAgent.findBugs', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage('No active editor');
            return;
        }

        const selection = editor.document.getText(editor.selection);
        if (!selection) {
            vscode.window.showErrorMessage('No code selected');
            return;
        }

        vscode.window.showInformationMessage('Finding bugs...');
        // TODO: Call Ollama API to find bugs
    });

    // Add commands to subscriptions
    context.subscriptions.push(
        openChatCommand,
        explainCodeCommand,
        refactorCodeCommand,
        generateTestsCommand,
        generateDocsCommand,
        findBugsCommand
    );

    // Show activation message
    const config = vscode.workspace.getConfiguration('ollamaAgent');
    const host = config.get<string>('host');
    vscode.window.showInformationMessage(`Ollama Agent connected to ${host}`);
}

export function deactivate() {
    console.log('Ollama Agent extension is now deactivated');
}
