// ExportDecompiledFunctions.java
// --------------------------------
// Ghidra script: decompiles a list of virtual addresses and writes each
// function's C pseudocode to a single output file.
//
// HOW TO RUN:
//   1. Open your binary in Ghidra and let auto-analysis finish.
//   2. Script Manager (Window → Script Manager) → green "+" to add script dir,
//      or paste this file into an existing script directory.
//   3. Edit TARGET_VAS below (or point VA_LIST_FILE at a text file of hex VAs).
//   4. Edit OUTPUT_FILE to the path where you want the report written.
//   5. Run. Progress appears in the Ghidra console.
//
// OUTPUT FORMAT per function:
//   ============================================================
//   FUNCTION: FunctionName
//   VA:       0x180760140
//   RVA:      0x760140
//   Signature: returnType FunctionName(params)
//   ------------------------------------------------------------
//   <decompiled C pseudocode>
//   ============================================================
//
// @author  investigation tooling
// @category Analysis
// @menupath Tools.Export.Decompile Functions by VA

import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.decompiler.DecompileOptions;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;

import java.io.FileWriter;
import java.io.BufferedWriter;
import java.io.BufferedReader;
import java.io.FileReader;
import java.io.File;
import java.util.ArrayList;
import java.util.List;

public class ExportDecompiledFunctions extends GhidraScript {

    // -----------------------------------------------------------------------
    // CONFIGURATION — edit these before running
    // -----------------------------------------------------------------------

    // Option A: hardcode VAs directly (hex strings, "0x" prefix optional).
    // Leave empty to use VA_LIST_FILE instead.
    private static final String[] TARGET_VAS = { };

    // Option B: path to a plain-text file with one hex VA per line.
    // Lines starting with '#' and blank lines are ignored.
    // Used only when TARGET_VAS is empty.
    private static final String VA_LIST_FILE = "C:\\Users\\TurnipKnight\\Documents\\GitHub\\MENACE_Research\\tools\\ghidra_scripts\\vaList.txt";

    // Where to write the report. If blank, defaults to:
    //   <project_dir>/decompiled_functions.txt
    private static final String OUTPUT_FILE = "C:\\Users\\TurnipKnight\\Documents\\GitHub\\MENACE_Research\\tools\\ghidra_scripts\\decompiled_functions.txt";

    // Decompiler timeout per function, in seconds.
    private static final int TIMEOUT_SECONDS = 60;

    // Image base of the binary (used to compute RVA in the report header).
    // Set to 0 if you don't need RVA annotations.
    private static final long IMAGE_BASE = 0x180000000L;

    // -----------------------------------------------------------------------
    // Script entry point
    // -----------------------------------------------------------------------

    @Override
    public void run() throws Exception {

        // ── Resolve output path ────────────────────────────────────────────
        String outPath = OUTPUT_FILE;
        if (outPath == null || outPath.isBlank()) {
            outPath = currentProgram.getDomainFile()
                          .getProjectLocator().getProjectDir()
                          .getAbsolutePath()
                      + File.separator + "decompiled_functions.txt";
        }

        // ── Collect target VAs ─────────────────────────────────────────────
        List<String> vaStrings = new ArrayList<>();
        if (TARGET_VAS != null && TARGET_VAS.length > 0) {
            for (String va : TARGET_VAS) {
                if (va != null && !va.isBlank()) vaStrings.add(va.strip());
            }
        } else if (VA_LIST_FILE != null && !VA_LIST_FILE.isBlank()) {
            vaStrings = loadVaFile(VA_LIST_FILE);
        }

        if (vaStrings.isEmpty()) {
            printerr("No target VAs configured. Edit TARGET_VAS or VA_LIST_FILE.");
            return;
        }

        println("Targets: " + vaStrings.size() + " VAs");
        println("Output : " + outPath);

        // ── Initialise decompiler ──────────────────────────────────────────
        DecompInterface decomp = new DecompInterface();
        DecompileOptions opts  = new DecompileOptions();
        decomp.setOptions(opts);
        decomp.setSimplificationStyle("decompile");

        if (!decomp.openProgram(currentProgram)) {
            printerr("Failed to open program in decompiler: " + decomp.getLastMessage());
            return;
        }

        // ── Decompile and write ────────────────────────────────────────────
        int success = 0, failure = 0;

        try (BufferedWriter writer = new BufferedWriter(new FileWriter(outPath))) {

            writer.write("Ghidra Decompilation Export");
            writer.newLine();
            writer.write("Program : " + currentProgram.getName());
            writer.newLine();
            writer.write("Image   : " + currentProgram.getImageBase());
            writer.newLine();
            writer.write("Functions: " + vaStrings.size());
            writer.newLine();
            writer.write("=".repeat(64));
            writer.newLine();
            writer.newLine();

            FunctionManager fm = currentProgram.getFunctionManager();

            for (String vaStr : vaStrings) {
                if (monitor.isCancelled()) break;

                // Parse address
                long vaLong;
                try {
                    vaLong = Long.decode(vaStr);  // handles 0x prefix
                } catch (NumberFormatException e) {
                    printerr("Skipping invalid VA: " + vaStr);
                    writeError(writer, vaStr, "Invalid VA format");
                    failure++;
                    continue;
                }

                Address addr = currentProgram.getAddressFactory()
                                   .getDefaultAddressSpace()
                                   .getAddress(vaLong);

                // Look up function at or containing this address
                Function func = fm.getFunctionAt(addr);
                if (func == null) {
                    func = fm.getFunctionContaining(addr);
                }

                if (func == null) {
                    printerr("No function at VA: " + vaStr);
                    writeError(writer, vaStr, "No function found at this address");
                    failure++;
                    continue;
                }

                println("Decompiling: " + func.getName() + " @ " + vaStr);
                monitor.setMessage("Decompiling " + func.getName());

                // Decompile
                DecompileResults result = decomp.decompileFunction(
                    func, TIMEOUT_SECONDS, monitor
                );

                // Write header block
                long rva = vaLong - IMAGE_BASE;
                writer.write("=".repeat(64));
                writer.newLine();
                writer.write("FUNCTION:  " + func.getName());
                writer.newLine();
                writer.write("VA:        " + vaStr);
                writer.newLine();
                if (IMAGE_BASE != 0) {
                    writer.write("RVA:       0x" + Long.toHexString(rva).toUpperCase());
                    writer.newLine();
                }
                writer.write("SIGNATURE: " + func.getSignature().getPrototypeString());
                writer.newLine();
                writer.write("ENTRY:     " + func.getEntryPoint());
                writer.newLine();
                writer.write("-".repeat(64));
                writer.newLine();

                if (result != null && result.decompileCompleted()) {
                    String code = result.getDecompiledFunction().getC();
                    writer.write(code != null ? code : "// [decompiler returned null body]");
                    success++;
                } else {
                    String msg = result != null ? result.getErrorMessage() : "timeout or null result";
                    writer.write("// [DECOMPILE FAILED: " + msg + "]");
                    printerr("Decompile failed for " + func.getName() + ": " + msg);
                    failure++;
                }

                writer.newLine();
                writer.newLine();
            }

            // Footer summary
            writer.write("=".repeat(64));
            writer.newLine();
            writer.write("SUMMARY: " + success + " succeeded, " + failure + " failed");
            writer.newLine();
        }

        decomp.dispose();

        println("");
        println("Done. " + success + " succeeded, " + failure + " failed.");
        println("Report written to: " + outPath);
    }

    // -----------------------------------------------------------------------
    // Helpers
    // -----------------------------------------------------------------------

    private List<String> loadVaFile(String path) throws Exception {
        List<String> vas = new ArrayList<>();
        try (BufferedReader reader = new BufferedReader(new FileReader(path))) {
            String line;
            while ((line = reader.readLine()) != null) {
                line = line.strip();
                if (line.isEmpty() || line.startsWith("#")) continue;
                // Support optional inline comment:  0x180760140   # Criterion.Score
                int commentIdx = line.indexOf('#');
                if (commentIdx > 0) line = line.substring(0, commentIdx).strip();
                if (!line.isEmpty()) vas.add(line);
            }
        }
        println("Loaded " + vas.size() + " VAs from: " + path);
        return vas;
    }

    private void writeError(BufferedWriter writer, String va, String reason) throws Exception {
        writer.write("=".repeat(64));
        writer.newLine();
        writer.write("VA:        " + va);
        writer.newLine();
        writer.write("ERROR:     " + reason);
        writer.newLine();
        writer.newLine();
    }
}
